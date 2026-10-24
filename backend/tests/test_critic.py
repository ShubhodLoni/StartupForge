from app.agents.critic import check_figures, extract_claims, run_critic_agent
from app.schemas import (
    ClaimVerdict,
    CompetitorAnalysis,
    CriticOutput,
    ResearchFindings,
    Source,
    StartupIdeaRequest,
)
from tests.conftest import COMPETITORS, REPORT, FakeLLM

REQ = StartupIdeaRequest(idea="AI receptionist for dental clinics")


def src(i, text):
    return Source(id=i, title=f"S{i}", url=f"https://e.org/{i}", snippet=text, query="q")


SOURCES = [
    src(1, "A 2025 survey found clinics miss 32% of calls."),
    src(2, "The dental software market reached $4.2 billion."),
]

RESEARCH = ResearchFindings(
    market_summary="Clinics miss 32% of calls [1]. The market is worth $4.2 billion [2].",
    target_customers=["Dental clinics"],
    pain_points=["Clinics lose 45% of new patients to voicemail [1]"],
    key_trends=["Spending reached $9 billion"],
    risks=[],
    assumptions_to_verify=[],
)
EMPTY_COMPETITORS = CompetitorAnalysis(competitors=[], alternatives=[], differentiation=[], market_gaps=[])


def test_extract_claims_keeps_sentence_and_location():
    claims = extract_claims({"research": RESEARCH.model_dump()}, {1, 2})
    assert [(c.location, c.source_ids) for c in claims] == [
        ("research.market_summary", [1]),
        ("research.market_summary", [2]),
        ("research.pain_points[0]", [1]),
    ]
    assert claims[1].text == "The market is worth $4.2 billion."
    assert claims[0].sentence == "Clinics miss 32% of calls [1]."


def test_figure_checks():
    docs = {"research": RESEARCH.model_dump(), "report": {"financial_summary": "Base MRR reaches $71,700 by month 24."}}
    flags = check_figures(docs, SOURCES, finance_text="- Base scenario: month-24 MRR $71,700")
    found = {(f.location, f.figure, f.issue) for f in flags}
    assert found == {
        ("research.pain_points[0]", "45%", "not_in_cited_source"),
        ("research.key_trends[0]", "$9 billion", "uncited"),
    }


def test_financial_summary_figures_must_come_from_the_model():
    docs = {"report": {"financial_summary": "Base MRR reaches $90,000."}}
    flags = check_figures(docs, [], finance_text="- Base scenario: month-24 MRR $71,700")
    assert [(f.figure, f.issue) for f in flags] == [("$90,000", "not_in_financial_model")]


async def test_critic_removes_unsupported_citations_and_records_verdicts():
    llm = FakeLLM()
    llm.outputs[CriticOutput] = CriticOutput(
        verdicts=[
            ClaimVerdict(claim_id=1, source_id=1, verdict="supported", reason="Matches."),
            ClaimVerdict(claim_id=2, source_id=2, verdict="partial", reason="Market defined differently."),
            ClaimVerdict(claim_id=3, source_id=1, verdict="unsupported", reason="Source doesn't mention 45%."),
        ]
    )
    report = REPORT.model_copy(update={"problem": "Manual booking is slow.", "executive_summary": "Summary."})
    result = await run_critic_agent(llm, REQ, RESEARCH, EMPTY_COMPETITORS, report, SOURCES)

    assert result.research.pain_points == ["Clinics lose 45% of new patients to voicemail"]
    assert result.research.market_summary == RESEARCH.market_summary
    fc = result.fact_check
    assert fc.claims_checked == 3
    assert fc.removed_citations == 1
    assert [(i.source_id, i.verdict) for i in fc.items] == [(1, "supported"), (2, "partial"), (1, "unsupported")]
    assert ("45%", "uncited") in {(f.figure, f.issue) for f in fc.figure_flags}

    prompt = llm.prompts_for(CriticOutput)[-1].content
    assert "C3 (cites 1): Clinics lose 45% of new patients to voicemail" in prompt
    assert "[2] S2\nThe dental software market reached $4.2 billion." in prompt


async def test_missing_verdicts_are_unchecked_and_keep_citations():
    llm = FakeLLM()
    llm.outputs[CriticOutput] = CriticOutput(verdicts=[])
    result = await run_critic_agent(llm, REQ, RESEARCH, EMPTY_COMPETITORS, REPORT, SOURCES)
    assert {i.verdict for i in result.fact_check.items} == {"unchecked"}
    assert result.fact_check.removed_citations == 0
    assert result.research.pain_points == RESEARCH.pain_points


async def test_no_llm_call_without_cited_claims():
    llm = FakeLLM()
    plain = RESEARCH.model_copy(update={"market_summary": "No citations.", "pain_points": []})
    result = await run_critic_agent(llm, REQ, plain, COMPETITORS, REPORT, [])
    assert llm.calls == []
    assert result.fact_check.claims_checked == 0
