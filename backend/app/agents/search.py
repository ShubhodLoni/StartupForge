import asyncio
import logging
from urllib.parse import urlsplit

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agents.common import format_idea
from app.rag import Chunk, chunk_text
from app.schemas import Retrieval, SearchPlan, Source, StartupIdeaRequest
from app.search import SearchResult

logger = logging.getLogger("startupforge")

SYSTEM_PROMPT = """You are the Search Agent in a team of startup analysts.
Write two kinds of web search queries for a startup idea:
- market queries: evidence about customer pain points, market size and growth reports, industry trends, regulation;
- competitor queries: existing companies, products, and tools that already solve this problem (e.g. "best X software", "X alternatives").
Make each query specific and different from the others. Do not search for the idea's own (hypothetical) brand name."""


class Page(BaseModel):
    result: SearchResult
    kind: str
    query: str


def _normalize_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.netloc.lower().removeprefix('www.')}{parts.path.rstrip('/')}"


def _dedupe(queries: list[str], limit: int) -> list[str]:
    return list(dict.fromkeys(q.strip() for q in queries if q.strip()))[:limit]


async def plan_queries(
    llm: BaseChatModel, req: StartupIdeaRequest, n_market: int, n_competitor: int
) -> list[tuple[str, str]]:
    plan = await llm.with_structured_output(SearchPlan).ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"{format_idea(req)}\n\n"
                f"Return exactly {n_market} market queries and {n_competitor} competitor queries."
            ),
        ]
    )
    plan = SearchPlan.model_validate(plan)
    market = _dedupe(plan.market_queries, n_market) or [req.idea[:200]]
    competitor = [q for q in _dedupe(plan.competitor_queries, n_competitor) if q not in market]
    return [(q, "market") for q in market] + [(q, "competitor") for q in competitor]


async def run_search_agent(
    llm: BaseChatModel,
    search_client,
    req: StartupIdeaRequest,
    *,
    num_queries: int = 3,
    num_competitor_queries: int = 2,
) -> tuple[list[Page], Retrieval]:
    if search_client is None:
        return [], Retrieval(status="disabled", detail="Web search is off: TAVILY_API_KEY is not set.")

    planned = await plan_queries(llm, req, num_queries, num_competitor_queries)
    queries = [q for q, _ in planned]
    outcomes = await asyncio.gather(*(search_client.search(q) for q in queries), return_exceptions=True)

    pages: list[Page] = []
    seen: set[str] = set()
    failures: list[str] = []
    for (query, kind), outcome in zip(planned, outcomes):
        if isinstance(outcome, BaseException):
            logger.warning("Search failed for %r: %s", query, outcome)
            failures.append(str(outcome))
            continue
        for result in outcome:
            key = _normalize_url(result.url)
            if key not in seen:
                seen.add(key)
                pages.append(Page(result=result, kind=kind, query=query))

    if failures and len(failures) == len(queries):
        return [], Retrieval(status="failed", queries=queries, detail=failures[0])
    if not pages:
        return [], Retrieval(status="no_results", queries=queries, detail="Search returned no results.")
    detail = f"{len(failures)} of {len(queries)} searches failed." if failures else None
    return pages, Retrieval(status="ok", queries=queries, detail=detail, pages=len(pages))


def pages_to_sources(pages: list[Page], snippet_chars: int = 600) -> list[Source]:
    return [
        Source(
            id=i,
            title=p.result.title,
            url=p.result.url,
            snippet=p.result.content[:snippet_chars],
            query=p.query,
            kind=p.kind,
            published_date=p.result.published_date,
        )
        for i, p in enumerate(pages, start=1)
    ]


def pages_to_chunks(
    pages: list[Page], chunk_size: int = 800, overlap: int = 120, max_page_chars: int = 8000
) -> list[Chunk]:
    chunks = []
    for p in pages:
        text = (p.result.raw_content or p.result.content)[:max_page_chars]
        for i, piece in enumerate(chunk_text(text, chunk_size, overlap)):
            chunks.append(
                Chunk(
                    url=p.result.url,
                    title=p.result.title,
                    kind=p.kind,
                    query=p.query,
                    published_date=p.result.published_date,
                    chunk_index=i,
                    text=piece,
                )
            )
    return chunks
