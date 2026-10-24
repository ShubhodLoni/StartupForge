import pytest
from fastapi.testclient import TestClient

from app.db import MemoryReportStore
from app.main import Services, app, get_llm, get_search_client, get_services
from app.schemas import (
    ClaimVerdict,
    Competitor,
    CriticOutput,
    CompetitorAnalysis,
    Feature,
    FinanceDraft,
    ProductPlan,
    ResearchFindings,
    SearchPlan,
    StartupReport,
)
from app.search import SearchError, SearchResult

Q_MISSED = "dental clinic missed calls statistics"
Q_BOOKING = "online booking adoption dental patients"
Q_COMPETITORS = "AI receptionist software for dental practices"

SEARCH_PLAN = SearchPlan(
    market_queries=[Q_MISSED, Q_BOOKING, Q_MISSED],
    competitor_queries=[Q_COMPETITORS],
)

RESEARCH = ResearchFindings(
    market_summary="Independent clinics struggle with scheduling overhead [1].",
    target_customers=["Small dental clinics"],
    pain_points=["Phone-based booking wastes staff time [1, 99]"],
    key_trends=["Patients increasingly expect online booking [2]"],
    risks=["Integration with legacy practice software"],
    assumptions_to_verify=["Share of clinics without online booking"],
)

COMPETITORS = CompetitorAnalysis(
    competitors=[
        Competitor(
            name="Acme Reception",
            description="AI phone answering for dental offices [4].",
            strengths=["Dental-specific [4]"],
            weaknesses=["Likely: limited integrations"],
            source_ids=[4, 1],
        ),
        Competitor(
            name="Ghost Corp",
            description="Invented competitor.",
            strengths=[],
            weaknesses=[],
            source_ids=[1],
        ),
    ],
    alternatives=["Front-desk staff answering phones"],
    differentiation=["Deep practice-software integration"],
    market_gaps=["After-hours booking [3]"],
    unverified_competitors=["model-supplied value must be ignored"],
)

PRODUCT = ProductPlan(
    product_vision="Never miss a patient call.",
    mvp_features=[
        Feature(name="Call answering", description="AI answers calls", priority="must"),
        Feature(name="Calendar sync", description="Books into the practice calendar [1]", priority="should"),
    ],
    user_journey=["Patient calls", "AI books slot"],
    differentiators=["Dental-specific workflows"],
    success_metrics=["Share of calls answered"],
    pricing_options=["Per-location monthly subscription"],
    build_risks=["Speech recognition accuracy"],
)

FINANCE_DRAFT = FinanceDraft(
    price_per_month=199,
    starting_customers=0,
    new_customers_month_1=5,
    new_customer_growth_pct=10,
    monthly_churn_pct=3,
    gross_margin_pct=120,
    cac=400,
    fixed_costs_per_month=15000,
    starting_cash=250000,
    rationale=["price_per_month: Estimate: typical SMB software price", "cac: survey figure [2] [42]"],
)

REPORT = StartupReport(
    title="ClinicFlow",
    executive_summary="AI scheduling assistant for small clinics [7].",
    problem="Manual booking is slow [1].",
    solution="An AI receptionist that books appointments.",
    value_proposition="Fewer missed calls, less admin.",
    target_customers=["Small dental clinics"],
    go_to_market=["Pilot with 5 local clinics"],
    risks=["Integration with legacy practice software"],
    next_steps=["Interview 20 clinic managers"],
    financial_summary="The base scenario projects month-24 MRR under editable assumptions.",
    verification_needed=["Share of clinics without online booking"],
)

CRITIC = CriticOutput(
    verdicts=[
        ClaimVerdict(claim_id=1, source_id=1, verdict="supported", reason="Source says clinics miss calls."),
        ClaimVerdict(claim_id=4, source_id=2, verdict="unsupported", reason="Source is about phone time, not booking."),
        ClaimVerdict(claim_id=7, source_id=3, verdict="partial", reason="Source mentions online booking only."),
        ClaimVerdict(claim_id=99, source_id=1, verdict="unsupported", reason="Bogus pair: must be ignored."),
    ]
)

SEARCH_RESULTS = {
    Q_MISSED: [
        SearchResult(title="Missed calls study", url="https://example.org/missed-calls", content="Clinics miss many calls."),
        SearchResult(title="Front desk survey", url="https://example.com/survey/", content="Staff spend hours on the phone."),
    ],
    Q_BOOKING: [
        SearchResult(title="Front desk survey", url="https://www.example.com/survey", content="Duplicate."),
        SearchResult(title="Booking trends", url="https://example.net/booking", content="Patients prefer online booking."),
    ],
    Q_COMPETITORS: [
        SearchResult(
            title="Top AI receptionists for dentists",
            url="https://example.io/ai-receptionists",
            content="Acme Reception offers AI phone answering built for dental offices.",
        ),
    ],
}


class _FakeStructured:
    def __init__(self, parent, schema):
        self.parent, self.schema = parent, schema

    async def ainvoke(self, messages):
        self.parent.calls.append((self.schema, messages))
        if self.parent.fail_on is self.schema:
            raise RuntimeError("upstream LLM failure")
        return self.parent.outputs[self.schema]


class FakeLLM:
    def __init__(self, fail_on=None):
        self.outputs = {
            SearchPlan: SEARCH_PLAN,
            ResearchFindings: RESEARCH,
            CompetitorAnalysis: COMPETITORS,
            ProductPlan: PRODUCT,
            FinanceDraft: FINANCE_DRAFT,
            StartupReport: REPORT,
            CriticOutput: CRITIC,
        }
        self.calls = []
        self.fail_on = fail_on

    def with_structured_output(self, schema):
        return _FakeStructured(self, schema)

    def prompts_for(self, schema):
        return next(messages for s, messages in self.calls if s is schema)

    def schemas_called(self):
        return [s for s, _ in self.calls]


class FakeSearch:
    def __init__(self, results=None, failing=()):
        self.results = SEARCH_RESULTS if results is None else results
        self.failing = set(failing)
        self.queries = []

    async def search(self, query):
        self.queries.append(query)
        if query in self.failing:
            raise SearchError("Tavily returned HTTP 500")
        return self.results.get(query, [])


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def fake_search():
    return FakeSearch()


@pytest.fixture
def services():
    return Services(MemoryReportStore(), None, "memory")


@pytest.fixture
def client(fake_llm, fake_search, services):
    app.dependency_overrides[get_llm] = lambda: fake_llm
    app.dependency_overrides[get_search_client] = lambda: fake_search
    app.dependency_overrides[get_services] = lambda: services
    yield TestClient(app)
    app.dependency_overrides.clear()
