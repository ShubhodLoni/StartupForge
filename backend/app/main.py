import json
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from sse_starlette.sse import EventSourceResponse

from app.citations import build_citations
from app.config import Settings, get_settings
from app.db import Database, MemoryReportStore, PgReportStore, PgVectorIndex
from app.finance import FinanceAssumptions, FinancialModel, build_model
from app.graph import AGENT_SEQUENCE, RagConfig, build_graph
from app.llm import LLMNotConfiguredError, build_llm
from app.rag import FastEmbedder, MemoryIndex
from app.schemas import FactCheck, ReportResponse, StartupIdeaRequest
from app.search import TavilySearch

logger = logging.getLogger("startupforge")


@dataclass
class Services:
    store: object
    rag: RagConfig | None
    storage: str
    db: Database | None = None


def _rag_config(settings: Settings, index) -> RagConfig | None:
    if not settings.rag_enabled:
        return None
    return RagConfig(
        index=index,
        embedder=FastEmbedder(settings.embedding_model, settings.embedding_dim),
        top_k=settings.rag_top_k,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        max_page_chars=settings.max_page_chars,
    )


async def create_services(settings: Settings) -> Services:
    if settings.database_url:
        db = Database(settings.database_url, settings.embedding_dim)
        await db.open()
        return Services(PgReportStore(db), _rag_config(settings, PgVectorIndex(db)), "postgres", db)
    return Services(MemoryReportStore(), _rag_config(settings, MemoryIndex()), "memory")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = await create_services(get_settings())
    yield
    if app.state.services.db:
        await app.state.services.db.close()


settings = get_settings()
app = FastAPI(title="StartupForge AI", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_services(request: Request) -> Services:
    services = getattr(request.app.state, "services", None)
    if services is None:
        services = request.app.state.services = Services(MemoryReportStore(), None, "memory")
    return services


def get_llm(settings: Settings = Depends(get_settings)) -> BaseChatModel:
    try:
        return build_llm(settings)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_search_client(settings: Settings = Depends(get_settings)) -> TavilySearch | None:
    if not settings.tavily_api_key:
        return None
    return TavilySearch(
        settings.tavily_api_key,
        max_results=settings.search_max_results,
        include_raw_content=settings.rag_enabled,
    )


def _graph(llm, search_client, settings: Settings, services: Services):
    return build_graph(
        llm,
        search_client,
        rag=services.rag,
        num_queries=settings.search_queries,
        num_competitor_queries=settings.competitor_queries,
        snippet_chars=settings.source_snippet_chars,
    )


def _build_response(req: StartupIdeaRequest, state: dict, model: str) -> ReportResponse:
    citations = build_citations(
        state["sources"], state["research"], state["competitors"], state["finance"], state["report"]
    )
    return ReportResponse(
        id=str(uuid.uuid4()),
        request=req,
        research=state["research"],
        competitors=state["competitors"],
        product=state["product"],
        finance=state["finance"],
        report=state["report"],
        fact_check=state.get("fact_check") or FactCheck(),
        citations=citations,
        retrieval=state["retrieval"],
        model=model,
        generated_at=datetime.now(timezone.utc),
        data_provenance="web_sources" if citations else "llm_knowledge_unverified",
    )


async def _save(services: Services, response: ReportResponse) -> None:
    try:
        await services.store.save(response.model_dump(mode="json"))
    except Exception:
        logger.exception("Failed to save report %s", response.id)


def _public_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc)[:300]}"


@app.get("/api/health")
def health(settings: Settings = Depends(get_settings), services: Services = Depends(get_services)):
    return {
        "status": "ok",
        "llm_configured": bool(settings.groq_api_key),
        "search_configured": bool(settings.tavily_api_key),
        "rag_enabled": services.rag is not None,
        "storage": services.storage,
        "model": settings.groq_model,
        "agents": AGENT_SEQUENCE,
    }


@app.post("/api/finance/projection", response_model=FinancialModel)
def finance_projection(assumptions: FinanceAssumptions):
    return build_model(assumptions)


@app.get("/api/reports")
async def list_reports(limit: int = Query(20, ge=1, le=100), services: Services = Depends(get_services)):
    return await services.store.list(limit)


@app.get("/api/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, services: Services = Depends(get_services)):
    report = await services.store.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.put("/api/reports/{report_id}/finance", response_model=FinancialModel)
async def update_report_finance(
    report_id: str, assumptions: FinanceAssumptions, services: Services = Depends(get_services)
):
    report = await services.store.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    current = FinancialModel.model_validate(report["finance"])
    model = build_model(assumptions, rationale=current.rationale)
    model.original_assumptions = current.original_assumptions or current.assumptions
    report["finance"] = model.model_dump(mode="json")
    await services.store.save(report)
    return model


@app.post("/api/reports", response_model=ReportResponse)
async def create_report(
    req: StartupIdeaRequest,
    llm: BaseChatModel = Depends(get_llm),
    search_client: TavilySearch | None = Depends(get_search_client),
    settings: Settings = Depends(get_settings),
    services: Services = Depends(get_services),
):
    try:
        state = await _graph(llm, search_client, settings, services).ainvoke({"request": req})
    except Exception as exc:
        logger.exception("Agent pipeline failed")
        raise HTTPException(status_code=502, detail=_public_error(exc)) from exc
    response = _build_response(req, state, settings.groq_model)
    await _save(services, response)
    return response


_HIDDEN_KEYS = {"run_id"}


@app.post("/api/reports/stream")
async def stream_report(
    req: StartupIdeaRequest,
    llm: BaseChatModel = Depends(get_llm),
    search_client: TavilySearch | None = Depends(get_search_client),
    settings: Settings = Depends(get_settings),
    services: Services = Depends(get_services),
):
    graph = _graph(llm, search_client, settings, services)

    async def events():
        state: dict = {"request": req}
        yield {"event": "agent_started", "data": json.dumps({"agent": AGENT_SEQUENCE[0]})}
        try:
            async for chunk in graph.astream({"request": req}, stream_mode="updates"):
                for node, update in chunk.items():
                    state.update(update)
                    payload = jsonable_encoder({k: v for k, v in update.items() if k not in _HIDDEN_KEYS})
                    yield {
                        "event": "agent_completed",
                        "data": json.dumps({"agent": node, "output": payload}),
                    }
                    idx = AGENT_SEQUENCE.index(node)
                    if idx + 1 < len(AGENT_SEQUENCE):
                        yield {
                            "event": "agent_started",
                            "data": json.dumps({"agent": AGENT_SEQUENCE[idx + 1]}),
                        }
            response = _build_response(req, state, settings.groq_model)
            await _save(services, response)
            yield {"event": "complete", "data": response.model_dump_json()}
        except Exception as exc:
            logger.exception("Agent pipeline failed")
            yield {"event": "error", "data": json.dumps({"detail": _public_error(exc)})}

    return EventSourceResponse(events())
