from app.graph import AGENT_SEQUENCE, build_graph
from app.schemas import (
    CompetitorAnalysis,
    FinanceDraft,
    ProductPlan,
    ResearchFindings,
    SearchPlan,
    StartupIdeaRequest,
    StartupReport,
    CriticOutput,
)
from tests.conftest import RESEARCH, FakeLLM, FakeSearch

REQ = StartupIdeaRequest(idea="AI receptionist for dental clinics", target_market="US")


async def test_graph_runs_all_agents_in_order():
    llm = FakeLLM()
    state = await build_graph(llm, FakeSearch()).ainvoke({"request": REQ})

    assert AGENT_SEQUENCE == ["search", "research", "competitor", "product", "finance", "report", "critic"]
    assert llm.schemas_called() == [
        SearchPlan, ResearchFindings, CompetitorAnalysis, ProductPlan, FinanceDraft, StartupReport, CriticOutput,
    ]
    assert state["retrieval"].status == "ok"
    assert len(state["sources"]) == 4
    assert [c.name for c in state["competitors"].competitors] == ["Acme Reception"]
    assert state["finance"].scenarios[1].name == "base"
    assert state["research"].pain_points == ["Phone-based booking wastes staff time [1]"]
    assert state["report"].executive_summary == "AI scheduling assistant for small clinics."
    assert state["report"].problem == "Manual booking is slow [1]."
    assert state["research"].key_trends == ["Patients increasingly expect online booking"]
    assert state["fact_check"].removed_citations == 1


async def test_sources_reach_research_and_report_prompts():
    llm = FakeLLM()
    await build_graph(llm, FakeSearch()).ainvoke({"request": REQ})

    for schema in (ResearchFindings, StartupReport):
        msgs = llm.prompts_for(schema)
        assert "[1] Missed calls study" in msgs[-1].content
        assert "https://example.net/booking" in msgs[-1].content
        assert "untrusted data" in msgs[0].content
    report_prompt = llm.prompts_for(StartupReport)[-1].content
    assert "Target market: US" in report_prompt
    assert RESEARCH.risks[0] in report_prompt
    assert "COMPUTED FINANCIAL MODEL" in report_prompt
    assert "Acme Reception" in report_prompt


async def test_without_search_all_markers_removed_and_prompt_says_no_sources():
    llm = FakeLLM()
    state = await build_graph(llm, None).ainvoke({"request": REQ})

    assert state["retrieval"].status == "disabled"
    assert state["sources"] == []
    assert state["research"].market_summary == "Independent clinics struggle with scheduling overhead."
    assert state["report"].problem == "Manual booking is slow."
    assert state["competitors"].competitors == []
    for schema in (ResearchFindings, StartupReport):
        msgs = llm.prompts_for(schema)
        assert "Never invent statistics" in msgs[0].content
        assert "No web sources were retrieved." in msgs[-1].content
