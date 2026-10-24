from app.graph import RagConfig, build_graph
from app.rag import Chunk, HashEmbedder, MemoryIndex, RunRetriever, chunk_text, register
from app.schemas import ResearchFindings, StartupIdeaRequest
from app.search import SearchResult
from tests.conftest import Q_BOOKING, Q_COMPETITORS, Q_MISSED, FakeLLM, FakeSearch


def chunk(url, i, text, kind="market"):
    return Chunk(url=url, title=url, kind=kind, query="q", chunk_index=i, text=text)


def test_chunks_respect_size_and_cover_all_text():
    text = " ".join(f"Sentence {i} talks about clinics and calls." for i in range(100))
    chunks = chunk_text(text, size=200, overlap=50)
    assert len(chunks) > 5
    assert all(len(c) <= 250 for c in chunks)
    for i in range(100):
        assert any(f"Sentence {i} " in c for c in chunks)


def test_chunks_overlap():
    text = " ".join(f"Sentence {i} is here." for i in range(40))
    first, second = chunk_text(text, size=120, overlap=40)[:2]
    assert first.split(". ")[-1].rstrip(".") in second


def test_short_text_is_one_chunk_and_long_words_are_split():
    assert chunk_text("Just one line.") == ["Just one line."]
    assert all(len(c) <= 50 for c in chunk_text("x" * 175, size=50, overlap=0))


async def test_retrieval_ranks_relevant_chunks_first():
    retriever = RunRetriever(MemoryIndex(), HashEmbedder(), "run-1")
    await retriever.index_chunks(
        [
            chunk("https://a.org", 0, "pricing plans per month subscription"),
            chunk("https://b.org", 0, "dental clinics miss phone calls"),
            chunk("https://c.org", 0, "weather in paris today"),
        ]
    )
    top = await retriever.retrieve("why do dental clinics miss calls", k=1)
    assert top[0].url == "https://b.org"


async def test_retrieval_is_scoped_to_run_and_kind():
    index, emb = MemoryIndex(), HashEmbedder()
    await RunRetriever(index, emb, "run-1").index_chunks([chunk("https://a.org", 0, "clinic calls", kind="competitor")])
    await RunRetriever(index, emb, "run-2").index_chunks([chunk("https://b.org", 0, "clinic calls")])
    r1 = RunRetriever(index, emb, "run-1")
    assert [c.url for c in await r1.retrieve("clinic calls", 5)] == ["https://a.org"]
    assert await r1.retrieve("clinic calls", 5, kinds=["market"]) == []


def test_register_assigns_stable_ids():
    a, b = chunk("https://a.org", 0, "A"), chunk("https://b.org", 2, "B")
    sources, selected = register([], [a, b])
    assert [s.id for s in selected] == [1, 2]
    assert selected[1].chunk_index == 2 and selected[1].snippet == "B"
    sources, selected = register(sources, [b, chunk("https://c.org", 0, "C"), b])
    assert [s.id for s in selected] == [2, 3]
    assert len(sources) == 3


LONG_PAGE = " ".join(
    ["Clinics miss many calls during lunch hours."] * 3
    + ["Front desk staff spend hours on the phone each day."] * 3
    + ["Unrelated paragraph about office furniture and decor."] * 6
)


def rag_search():
    results = {
        Q_MISSED: [SearchResult(title="Study", url="https://example.org/study", content="excerpt", raw_content=LONG_PAGE)],
        Q_BOOKING: [SearchResult(title="Trends", url="https://example.net/trends", content="Patients prefer online booking.")],
        Q_COMPETITORS: [
            SearchResult(title="Top AI receptionists", url="https://example.io/ai", content="Acme Reception offers AI phone answering for dental offices.")
        ],
    }
    return FakeSearch(results=results)


REQ = StartupIdeaRequest(idea="AI receptionist for dental clinics")


async def test_graph_rag_mode_registers_retrieved_chunks_as_sources():
    llm = FakeLLM()
    rag = RagConfig(index=MemoryIndex(), embedder=HashEmbedder(), top_k=3, chunk_size=120, chunk_overlap=0)
    state = await build_graph(llm, rag_search(), rag=rag).ainvoke({"request": REQ})

    assert state["retrieval"].mode == "rag"
    assert state["retrieval"].pages == 3
    assert state["retrieval"].chunks > 3
    sources = state["sources"]
    assert [s.id for s in sources] == list(range(1, len(sources) + 1))
    for s in sources:
        assert s.snippet in LONG_PAGE or s.snippet in {"Patients prefer online booking.", "Acme Reception offers AI phone answering for dental offices."}
    research_prompt = llm.prompts_for(ResearchFindings)[-1].content
    assert research_prompt.count("\nURL: ") == 3


class BrokenEmbedder(HashEmbedder):
    async def embed_documents(self, texts):
        raise RuntimeError("model download failed")


async def test_graph_falls_back_to_snippets_when_embedding_fails():
    rag = RagConfig(index=MemoryIndex(), embedder=BrokenEmbedder())
    state = await build_graph(FakeLLM(), rag_search(), rag=rag).ainvoke({"request": REQ})
    assert state["retrieval"].mode == "snippets"
    assert "RAG unavailable" in state["retrieval"].detail
    assert [s.snippet for s in state["sources"]][0] == "excerpt"
