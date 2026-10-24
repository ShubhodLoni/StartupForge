from app.agents.competitor import run_competitor_agent, verify_competitors
from app.agents.finance import finance_brief, run_finance_agent
from app.agents.product import run_product_agent
from app.agents.search import pages_to_sources, run_search_agent
from app.schemas import Competitor, CompetitorAnalysis, Source, StartupIdeaRequest
from tests.conftest import COMPETITORS, PRODUCT, RESEARCH, FakeLLM, FakeSearch

REQ = StartupIdeaRequest(idea="AI receptionist for small dental clinics")


async def sources():
    pages, _ = await run_search_agent(FakeLLM(), FakeSearch(), REQ)
    return pages_to_sources(pages)


def src(i, text):
    return Source(id=i, title="T", url=f"https://e.org/{i}", snippet=text, query="q")


async def test_competitor_agent_keeps_only_source_backed_competitors():
    result = await run_competitor_agent(FakeLLM(), REQ, RESEARCH, await sources())

    assert [c.name for c in result.competitors] == ["Acme Reception"]
    assert result.competitors[0].source_ids == [4]
    assert result.unverified_competitors == ["Ghost Corp"]
    assert result.market_gaps == ["After-hours booking [3]"]


async def test_competitor_agent_without_sources_drops_all_named_competitors():
    llm = FakeLLM()
    result = await run_competitor_agent(llm, REQ, RESEARCH, [])
    assert result.competitors == []
    assert set(result.unverified_competitors) == {"Acme Reception", "Ghost Corp"}
    assert result.market_gaps == ["After-hours booking"]
    assert "MUST be an empty list" in llm.prompts_for(CompetitorAnalysis)[0].content


def test_name_matching_uses_word_boundaries():
    analysis = CompetitorAnalysis(
        competitors=[Competitor(name="Ada", description="", strengths=[], weaknesses=[], source_ids=[1])],
        alternatives=[], differentiation=[], market_gaps=[],
    )
    assert verify_competitors(analysis, [src(1, "Clinics in Canada")]).competitors == []
    assert len(verify_competitors(analysis, [src(1, "Ada, a chatbot vendor")]).competitors) == 1


def test_name_matching_is_case_insensitive():
    analysis = COMPETITORS.model_copy(update={"competitors": COMPETITORS.competitors[:1]})
    kept = verify_competitors(analysis, [src(4, "ACME RECEPTION launched")]).competitors
    assert len(kept) == 1


async def test_product_agent_strips_markers():
    plan = await run_product_agent(FakeLLM(), REQ, RESEARCH, COMPETITORS)
    assert plan.mvp_features[1].description == "Books into the practice calendar"


async def test_finance_agent_sanitizes_and_computes():
    model = await run_finance_agent(FakeLLM(), REQ, PRODUCT, await sources())

    assert model.assumptions.gross_margin_pct == 100
    assert any("gross_margin_pct" in note for note in model.adjustments)
    assert model.rationale == ["price_per_month: Estimate: typical SMB software price", "cac: survey figure [2]"]
    assert [s.name for s in model.scenarios] == ["conservative", "base", "optimistic"]
    base = model.scenarios[1].projection
    assert len(base.rows) == 24
    assert base.rows[0].mrr == 995
    assert base.rows[0].net_income == 995 - 5 * 400 - 15000


async def test_finance_brief_contains_only_computed_numbers():
    model = await run_finance_agent(FakeLLM(), REQ, PRODUCT, [])
    brief = finance_brief(model)
    base = model.scenarios[1].projection.metrics
    assert f"${base.ending_mrr:,.0f}" in brief
    assert "Conservative scenario" in brief and "Optimistic scenario" in brief
