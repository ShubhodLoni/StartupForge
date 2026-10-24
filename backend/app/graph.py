import logging
import uuid
from dataclasses import dataclass
from typing import TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.agents.competitor import run_competitor_agent
from app.agents.critic import run_critic_agent
from app.agents.finance import finance_brief, run_finance_agent
from app.agents.product import run_product_agent
from app.agents.report import run_report_agent
from app.agents.research import run_research_agent
from app.agents.search import pages_to_chunks, pages_to_sources, run_search_agent
from app.citations import clean_model
from app.finance import FinancialModel
from app.rag import Embedder, RunRetriever, VectorIndex, register
from app.schemas import (
    CompetitorAnalysis,
    FactCheck,
    ProductPlan,
    ResearchFindings,
    Retrieval,
    Source,
    StartupIdeaRequest,
    StartupReport,
)

logger = logging.getLogger("startupforge")

AGENT_SEQUENCE = ["search", "research", "competitor", "product", "finance", "report", "critic"]


@dataclass
class RagConfig:
    index: VectorIndex
    embedder: Embedder
    top_k: int = 6
    chunk_size: int = 800
    chunk_overlap: int = 120
    max_page_chars: int = 8000


class PipelineState(TypedDict, total=False):
    request: StartupIdeaRequest
    run_id: str
    sources: list[Source]
    retrieval: Retrieval
    research: ResearchFindings
    competitors: CompetitorAnalysis
    product: ProductPlan
    finance: FinancialModel
    report: StartupReport
    fact_check: FactCheck


def build_graph(
    llm: BaseChatModel,
    search_client=None,
    *,
    rag: RagConfig | None = None,
    num_queries: int = 3,
    num_competitor_queries: int = 2,
    snippet_chars: int = 600,
):
    def retriever(state) -> RunRetriever:
        return RunRetriever(rag.index, rag.embedder, state["run_id"])

    async def select_sources(state, query: str, k: int | None = None) -> tuple[list[Source], list[Source]]:
        if state["retrieval"].mode != "rag":
            return state["sources"], state["sources"]
        chunks = await retriever(state).retrieve(query, k or rag.top_k)
        return register(state["sources"], chunks)

    async def search_node(state: PipelineState) -> PipelineState:
        run_id = str(uuid.uuid4())
        pages, retrieval = await run_search_agent(
            llm,
            search_client,
            state["request"],
            num_queries=num_queries,
            num_competitor_queries=num_competitor_queries,
        )
        if pages and rag is not None:
            chunks = pages_to_chunks(pages, rag.chunk_size, rag.chunk_overlap, rag.max_page_chars)
            try:
                await RunRetriever(rag.index, rag.embedder, run_id).index_chunks(chunks)
                retrieval = retrieval.model_copy(update={"mode": "rag", "chunks": len(chunks)})
                return {"run_id": run_id, "sources": [], "retrieval": retrieval}
            except Exception as exc:
                logger.exception("RAG indexing failed; falling back to search snippets")
                note = f"RAG unavailable ({type(exc).__name__}); used search snippets."
                retrieval = retrieval.model_copy(update={"detail": " ".join(filter(None, [retrieval.detail, note]))})
        return {"run_id": run_id, "sources": pages_to_sources(pages, snippet_chars), "retrieval": retrieval}

    async def research_node(state: PipelineState) -> PipelineState:
        req = state["request"]
        sources, shown = await select_sources(
            state, f"{req.idea} customers pain points market size growth trends regulation risks"
        )
        research = await run_research_agent(llm, req, shown)
        return {"research": clean_model(research, shown)[0], "sources": sources}

    async def competitor_node(state: PipelineState) -> PipelineState:
        req = state["request"]
        sources, shown = await select_sources(
            state, f"{req.idea} competitors alternatives existing products companies tools"
        )
        competitors = await run_competitor_agent(llm, req, state["research"], shown)
        return {"competitors": competitors, "sources": sources}

    async def product_node(state: PipelineState) -> PipelineState:
        product = await run_product_agent(llm, state["request"], state["research"], state["competitors"])
        return {"product": product}

    async def finance_node(state: PipelineState) -> PipelineState:
        req = state["request"]
        sources, shown = await select_sources(
            state, f"{req.idea} pricing price per month subscription cost customer acquisition churn", k=4
        )
        finance = await run_finance_agent(llm, req, state["product"], shown)
        return {"finance": finance, "sources": sources}

    async def report_node(state: PipelineState) -> PipelineState:
        sources = state["sources"]
        report = await run_report_agent(
            llm,
            state["request"],
            state["research"],
            sources,
            competitors=state["competitors"],
            product=state["product"],
            finance=state["finance"],
        )
        return {"report": clean_model(report, sources)[0]}

    async def critic_node(state: PipelineState) -> PipelineState:
        result = await run_critic_agent(
            llm,
            state["request"],
            state["research"],
            state["competitors"],
            state["report"],
            state["sources"],
            finance_text=finance_brief(state["finance"]),
        )
        return {
            "research": result.research,
            "competitors": result.competitors,
            "report": result.report,
            "fact_check": result.fact_check,
        }

    nodes = {
        "search": search_node,
        "research": research_node,
        "competitor": competitor_node,
        "product": product_node,
        "finance": finance_node,
        "report": report_node,
        "critic": critic_node,
    }
    graph = StateGraph(PipelineState)
    for name in AGENT_SEQUENCE:
        graph.add_node(name, nodes[name])
    graph.add_edge(START, AGENT_SEQUENCE[0])
    for a, b in zip(AGENT_SEQUENCE, AGENT_SEQUENCE[1:]):
        graph.add_edge(a, b)
    graph.add_edge(AGENT_SEQUENCE[-1], END)
    return graph.compile()
