import json

import httpx
import pytest

from app.agents.search import pages_to_chunks, pages_to_sources, run_search_agent
from app.schemas import StartupIdeaRequest
from app.search import SearchError, TavilySearch
from tests.conftest import Q_BOOKING, Q_COMPETITORS, Q_MISSED, FakeLLM, FakeSearch

REQ = StartupIdeaRequest(idea="AI receptionist for small dental clinics")


async def test_tavily_request_and_parsing():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "query": "q",
                "results": [
                    {"title": "A", "url": "https://a.org", "content": "alpha", "score": 0.9,
                     "published_date": "2026-01-02"},
                    {"title": "No content", "url": "https://b.org", "content": ""},
                ],
            },
        )

    client = TavilySearch("tvly-test", max_results=4, transport=httpx.MockTransport(handler))
    results = await client.search("dental scheduling")

    assert seen["url"] == "https://api.tavily.com/search"
    assert seen["auth"] == "Bearer tvly-test"
    assert seen["body"]["query"] == "dental scheduling"
    assert seen["body"]["max_results"] == 4
    assert [r.url for r in results] == ["https://a.org"]
    assert results[0].published_date == "2026-01-02"


async def test_tavily_http_error_raises():
    transport = httpx.MockTransport(lambda r: httpx.Response(401, json={"detail": "bad key"}))
    with pytest.raises(SearchError, match="HTTP 401"):
        await TavilySearch("bad", transport=transport).search("q")


async def test_search_agent_dedupes_and_numbers_sources():
    search = FakeSearch()
    pages, retrieval = await run_search_agent(FakeLLM(), search, REQ, num_queries=3)
    sources = pages_to_sources(pages)

    assert retrieval.status == "ok"
    assert retrieval.pages == 4
    assert retrieval.queries == [Q_MISSED, Q_BOOKING, Q_COMPETITORS]
    assert [s.id for s in sources] == [1, 2, 3, 4]
    assert [s.url for s in sources] == [
        "https://example.org/missed-calls",
        "https://example.com/survey/",
        "https://example.net/booking",
        "https://example.io/ai-receptionists",
    ]
    assert [s.kind for s in sources] == ["market", "market", "market", "competitor"]
    assert sources[0].snippet == "Clinics miss many calls."


async def test_search_agent_truncates_snippets():
    pages, _ = await run_search_agent(FakeLLM(), FakeSearch(), REQ)
    assert pages_to_sources(pages, snippet_chars=5)[0].snippet == "Clini"


async def test_search_agent_disabled_without_client():
    llm = FakeLLM()
    sources, retrieval = await run_search_agent(llm, None, REQ)
    assert sources == []
    assert retrieval.status == "disabled"
    assert llm.calls == []


async def test_search_agent_all_failed():
    failing = [Q_MISSED, Q_BOOKING, Q_COMPETITORS]
    sources, retrieval = await run_search_agent(FakeLLM(), FakeSearch(failing=failing), REQ)
    assert sources == []
    assert retrieval.status == "failed"
    assert "HTTP 500" in retrieval.detail


async def test_search_agent_partial_failure_keeps_results():
    search = FakeSearch(failing=[Q_MISSED])
    pages, retrieval = await run_search_agent(FakeLLM(), search, REQ)
    assert retrieval.status == "ok"
    assert retrieval.detail == "1 of 3 searches failed."
    assert [s.id for s in pages_to_sources(pages)] == [1, 2, 3]


async def test_search_agent_no_results():
    sources, retrieval = await run_search_agent(FakeLLM(), FakeSearch(results={}), REQ)
    assert sources == []
    assert retrieval.status == "no_results"


async def test_pages_to_chunks_prefers_full_text():
    from app.agents.search import Page
    from app.search import SearchResult

    long_text = " ".join(f"Sentence number {i} about dental clinics." for i in range(60))
    pages = [
        Page(result=SearchResult(title="A", url="https://a.org", content="short excerpt", raw_content=long_text), kind="market", query="q"),
        Page(result=SearchResult(title="B", url="https://b.org", content="only an excerpt here"), kind="competitor", query="q2"),
    ]
    chunks = pages_to_chunks(pages, chunk_size=300, overlap=60)
    a = [c for c in chunks if c.url == "https://a.org"]
    b = [c for c in chunks if c.url == "https://b.org"]
    assert len(a) > 1 and all(len(c.text) <= 360 for c in a)
    assert [c.chunk_index for c in a] == list(range(len(a)))
    assert [c.text for c in b] == ["only an excerpt here"]
    assert b[0].kind == "competitor"


async def test_tavily_requests_raw_content_when_enabled():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"results": [{"title": "A", "url": "https://a.org", "content": "x", "raw_content": "full"}]})

    results = await TavilySearch("k", include_raw_content=True, transport=httpx.MockTransport(handler)).search("q")
    assert seen["body"]["include_raw_content"] == "text"
    assert results[0].raw_content == "full"
