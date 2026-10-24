from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from app.finance import FinancialModel


class StartupIdeaRequest(BaseModel):
    idea: str = Field(..., min_length=10, max_length=2000, description="The startup idea to analyze")
    target_market: str | None = Field(None, max_length=200)
    industry: str | None = Field(None, max_length=100)


class SearchPlan(BaseModel):
    market_queries: list[str] = Field(
        ..., description="Queries about customers, pain points, market size, trends, regulation"
    )
    competitor_queries: list[str] = Field(
        ..., description="Queries that surface existing companies and products solving this problem"
    )


class Source(BaseModel):
    id: int
    title: str
    url: str
    snippet: str
    query: str
    kind: Literal["market", "competitor"] = "market"
    published_date: str | None = None
    chunk_index: int = 0


class Retrieval(BaseModel):
    status: Literal["ok", "disabled", "failed", "no_results"]
    queries: list[str] = Field(default_factory=list)
    detail: str | None = None
    mode: Literal["rag", "snippets"] = "snippets"
    pages: int = 0
    chunks: int = 0


class ResearchFindings(BaseModel):
    market_summary: str = Field(..., description="2-4 sentence overview of the market")
    target_customers: list[str] = Field(..., description="Distinct customer segments")
    pain_points: list[str] = Field(..., description="Problems these customers face")
    key_trends: list[str] = Field(..., description="Relevant industry trends")
    risks: list[str] = Field(..., description="Market, execution, or regulatory risks")
    assumptions_to_verify: list[str] = Field(
        ..., description="Claims that must be checked against real sources before relying on them"
    )


class Competitor(BaseModel):
    name: str = Field(..., description="Company or product name exactly as written in a source")
    description: str = Field(..., description="What it offers, per the sources")
    strengths: list[str]
    weaknesses: list[str]
    source_ids: list[int] = Field(..., description="Ids of sources that name this competitor")


class CompetitorAnalysis(BaseModel):
    competitors: list[Competitor] = Field(
        ..., description="Only companies explicitly named in the provided sources; empty if none"
    )
    alternatives: list[str] = Field(..., description="How target customers solve the problem today")
    differentiation: list[str] = Field(..., description="How the startup could stand apart")
    market_gaps: list[str] = Field(..., description="Unmet needs the competition leaves open")
    unverified_competitors: SkipJsonSchema[list[str]] = Field(
        default_factory=list,
        description="Set by the backend: names the model gave that no cited source mentions",
    )


class Feature(BaseModel):
    name: str
    description: str
    priority: Literal["must", "should", "could"]


class ProductPlan(BaseModel):
    product_vision: str = Field(..., description="One or two sentences")
    mvp_features: list[Feature] = Field(..., description="4-8 features, prioritized MoSCoW-style")
    user_journey: list[str] = Field(..., description="Ordered steps of the core user flow")
    differentiators: list[str]
    success_metrics: list[str] = Field(..., description="What to measure; no invented target numbers")
    pricing_options: list[str] = Field(..., description="Candidate pricing models, described qualitatively")
    build_risks: list[str]


class FinanceDraft(BaseModel):
    price_per_month: float = Field(..., description="Average revenue per customer per month, USD")
    starting_customers: float = Field(..., description="Paying customers at launch (usually 0)")
    new_customers_month_1: float = Field(..., description="New paying customers in month 1")
    new_customer_growth_pct: float = Field(..., description="Monthly growth of new-customer acquisition, percent (e.g. 10 = 10%)")
    monthly_churn_pct: float = Field(..., description="Monthly customer churn, percent (e.g. 3 = 3%)")
    gross_margin_pct: float = Field(..., description="Gross margin, percent (e.g. 75 = 75%)")
    cac: float = Field(..., description="Customer acquisition cost, USD")
    fixed_costs_per_month: float = Field(..., description="Monthly fixed costs (team, tools), USD")
    starting_cash: float = Field(..., description="Starting cash, USD")
    rationale: list[str] = Field(..., description="One line per assumption: '<field>: why this value'")


class ClaimVerdict(BaseModel):
    claim_id: int
    source_id: int
    verdict: Literal["supported", "partial", "unsupported"]
    reason: str = Field(..., description="One short sentence")


class CriticOutput(BaseModel):
    verdicts: list[ClaimVerdict]


class FactCheckItem(BaseModel):
    location: str
    claim: str
    source_id: int
    verdict: Literal["supported", "partial", "unsupported", "unchecked"]
    reason: str | None = None


class FigureFlag(BaseModel):
    location: str
    text: str
    figure: str
    issue: Literal["not_in_cited_source", "uncited", "not_in_financial_model"]


class FactCheck(BaseModel):
    claims_checked: int = 0
    items: list[FactCheckItem] = Field(default_factory=list)
    removed_citations: int = 0
    figure_flags: list[FigureFlag] = Field(default_factory=list)


class StartupReport(BaseModel):
    title: str
    executive_summary: str
    problem: str
    solution: str
    value_proposition: str
    target_customers: list[str]
    go_to_market: list[str] = Field(..., description="Concrete go-to-market steps")
    risks: list[str]
    next_steps: list[str] = Field(..., description="Actionable next steps for the founder")
    financial_summary: str = Field(
        ..., description="2-3 sentences using only figures from the computed financial model"
    )
    verification_needed: list[str] = Field(
        ..., description="Open questions and claims needing validation with real data"
    )


class Citation(BaseModel):
    id: int
    title: str
    url: str
    snippet: str | None = None


class ReportResponse(BaseModel):
    id: str
    request: StartupIdeaRequest
    research: ResearchFindings
    competitors: CompetitorAnalysis
    product: ProductPlan
    finance: FinancialModel
    report: StartupReport
    fact_check: FactCheck = Field(default_factory=FactCheck)
    citations: list[Citation] = Field(
        default_factory=list,
        description="Retrieved sources actually cited in the text; never generated by the LLM",
    )
    retrieval: Retrieval
    model: str
    generated_at: datetime
    data_provenance: Literal["web_sources", "llm_knowledge_unverified"]
