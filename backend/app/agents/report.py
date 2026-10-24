from langchain_core.language_models.chat_models import BaseChatModel

from app.agents.common import ask, format_idea, format_sources, grounding_rules
from app.agents.finance import finance_brief
from app.finance import FinancialModel
from app.schemas import (
    CompetitorAnalysis,
    ProductPlan,
    ResearchFindings,
    Source,
    StartupIdeaRequest,
    StartupReport,
)

REPORT_SNIPPET_CHARS = 300


def system_prompt(sources: list[Source]) -> str:
    return f"""You are the Report Agent in a team of startup analysts.
You receive a startup idea and the outputs of the Research, Competitor, Product, and Finance agents,
and write a clear, founder-ready startup brief. Build on their work; do not contradict it without saying why.
Keep every section tight and concrete. When you reuse a cited claim, keep its [n] markers.

{grounding_rules(sources)}

Financial rules:
- financial_summary may ONLY use figures that appear in the COMPUTED FINANCIAL MODEL block, copied exactly.
- Describe them as projections that depend on editable assumptions, not as forecasts.

Carry every item from the research's assumptions_to_verify into verification_needed, adding any new ones."""


async def run_report_agent(
    llm: BaseChatModel,
    req: StartupIdeaRequest,
    research: ResearchFindings,
    sources: list[Source] | None = None,
    competitors: CompetitorAnalysis | None = None,
    product: ProductPlan | None = None,
    finance: FinancialModel | None = None,
) -> StartupReport:
    sources = sources or []
    parts = [
        format_idea(req),
        f"Research findings (JSON):\n{research.model_dump_json(indent=2)}",
    ]
    if competitors is not None:
        parts.append(f"Competitor analysis (JSON):\n{competitors.model_dump_json(indent=2)}")
    if product is not None:
        parts.append(f"Product plan (JSON):\n{product.model_dump_json(indent=2)}")
    if finance is not None:
        parts.append(f"COMPUTED FINANCIAL MODEL (deterministic, 3 scenarios):\n{finance_brief(finance)}")
    parts.append(format_sources(sources, REPORT_SNIPPET_CHARS))
    return await ask(llm, StartupReport, system_prompt(sources), "\n\n".join(parts))
