import re

from pydantic import BaseModel

from app.schemas import Citation, Source

CITE_RE = re.compile(r"\s*\[(\d+(?:\s*,\s*\d+)*)\]")


def clean_markers(text: str, valid_ids: set[int]) -> tuple[str, set[int]]:
    used: set[int] = set()

    def replace(match: re.Match) -> str:
        ids = [int(n) for n in re.findall(r"\d+", match.group(1))]
        kept = sorted({i for i in ids if i in valid_ids})
        used.update(kept)
        return f" [{', '.join(map(str, kept))}]" if kept else ""

    return CITE_RE.sub(replace, text), used


def _walk(value, valid_ids: set[int], used: set[int]):
    if isinstance(value, str):
        text, ids = clean_markers(value, valid_ids)
        used.update(ids)
        return text
    if isinstance(value, list):
        return [_walk(v, valid_ids, used) for v in value]
    if isinstance(value, dict):
        return {k: _walk(v, valid_ids, used) for k, v in value.items()}
    return value


def clean_model[M: BaseModel](model: M, sources: list[Source]) -> tuple[M, set[int]]:
    used: set[int] = set()
    cleaned = _walk(model.model_dump(), {s.id for s in sources}, used)
    return type(model).model_validate(cleaned), used


def build_citations(sources: list[Source], *models: BaseModel) -> list[Citation]:
    used: set[int] = set()
    for model in models:
        used |= clean_model(model, sources)[1]
    return [
        Citation(id=s.id, title=s.title, url=s.url, snippet=s.snippet)
        for s in sources
        if s.id in used
    ]
