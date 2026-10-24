import asyncio
import hashlib
import math
import re
from collections import defaultdict
from typing import Protocol

from pydantic import BaseModel

from app.schemas import Source


class Chunk(BaseModel):
    url: str
    title: str
    kind: str
    query: str
    published_date: str | None = None
    chunk_index: int
    text: str

    @property
    def key(self) -> tuple[str, int]:
        return (self.url, self.chunk_index)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    text = re.sub(r"[ \t\r\f\v]+", " ", text).strip()
    pieces: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(text):
        sentence = sentence.strip()
        while len(sentence) > size:
            cut = sentence.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            pieces.append(sentence)

    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for piece in pieces:
        if current and length + len(piece) + 1 > size:
            chunks.append(" ".join(current))
            kept: list[str] = []
            kept_len = 0
            for prev in reversed(current):
                if kept_len + len(prev) + 1 > overlap:
                    break
                kept.insert(0, prev)
                kept_len += len(prev) + 1
            current, length = kept, kept_len
        current.append(piece)
        length += len(piece) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


class Embedder(Protocol):
    dim: int

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


class FastEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dim: int = 384):
        self.model_name = model_name
        self.dim = dim
        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(self.model_name)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(lambda: [v.tolist() for v in self._load().embed(texts)])

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(lambda: next(iter(self._load().query_embed(text))).tolist())


class HashEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            v[int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class VectorIndex(Protocol):
    async def add(self, run_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
    async def search(
        self, run_id: str, vector: list[float], k: int, kinds: list[str] | None = None
    ) -> list[Chunk]: ...


class MemoryIndex:
    def __init__(self):
        self._rows: dict[str, list[tuple[Chunk, list[float]]]] = defaultdict(list)

    async def add(self, run_id, chunks, vectors):
        self._rows[run_id].extend(zip(chunks, vectors))

    async def search(self, run_id, vector, k, kinds=None):
        rows = [r for r in self._rows.get(run_id, []) if kinds is None or r[0].kind in kinds]
        scored = sorted(rows, key=lambda r: -sum(a * b for a, b in zip(r[1], vector)))
        return [c for c, _ in scored[:k]]


class RunRetriever:
    def __init__(self, index: VectorIndex, embedder: Embedder, run_id: str):
        self.index, self.embedder, self.run_id = index, embedder, run_id

    async def index_chunks(self, chunks: list[Chunk]) -> None:
        if chunks:
            vectors = await self.embedder.embed_documents([c.text for c in chunks])
            await self.index.add(self.run_id, chunks, vectors)

    async def retrieve(self, query: str, k: int, kinds: list[str] | None = None) -> list[Chunk]:
        return await self.index.search(self.run_id, await self.embedder.embed_query(query), k, kinds)


def register(sources: list[Source], chunks: list[Chunk]) -> tuple[list[Source], list[Source]]:
    by_key = {(s.url, s.chunk_index): s for s in sources}
    all_sources = list(sources)
    selected = []
    for c in chunks:
        src = by_key.get(c.key)
        if src is None:
            src = Source(
                id=len(all_sources) + 1,
                title=c.title,
                url=c.url,
                snippet=c.text,
                query=c.query,
                kind=c.kind,
                published_date=c.published_date,
                chunk_index=c.chunk_index,
            )
            by_key[c.key] = src
            all_sources.append(src)
        if src not in selected:
            selected.append(src)
    return all_sources, selected
