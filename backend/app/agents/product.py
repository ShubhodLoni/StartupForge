from langchain_core.language_models.chat_models import BaseChatModel

from app.agents.common import GROUNDING_RULES, ask, format_idea
from app.citations import clean_model
from app.schemas import CompetitorAnalysis, ProductPlan, ResearchFindings, StartupIdeaRequest

SYSTEM_PROMPT = f"""You are the Product Agent in a team of startup analysts.
Turn the research and competitor analysis into a focused MVP plan: the product vision, a short prioritized
feature list (must / should / could), the core user journey, differentiators, success metrics, pricing model options,
and build risks.

{GROUNDING_RULES}

Product rules:
- Keep the MVP small: at most 3 "must" features.
- Success metrics name WHAT to measure (e.g. "weekly active clinics"); do not invent target values.
- Pricing options describe models (per seat, usage-based, tiered); do not state market prices."""


async def run_product_agent(
    llm: BaseChatModel,
    req: StartupIdeaRequest,
    research: ResearchFindings,
    competitors: CompetitorAnalysis,
) -> ProductPlan:
    human = (
        f"{format_idea(req)}\n\n"
        f"Research findings (JSON):\n{research.model_dump_json(indent=2)}\n\n"
        f"Competitor analysis (JSON):\n{competitors.model_dump_json(indent=2)}"
    )
    plan = await ask(llm, ProductPlan, SYSTEM_PROMPT, human)
    return clean_model(plan, [])[0]
