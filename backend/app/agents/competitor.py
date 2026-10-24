import re

from langchain_core.language_models.chat_models import BaseChatModel

from app.agents.common import ask, format_idea, format_sources, grounding_rules
from app.citations import clean_model
from app.schemas import CompetitorAnalysis, ResearchFindings, Source, StartupIdeaRequest

SNIPPET_CHARS = 800


def system_prompt(sources: list[Source]) -> str:
    competitor_rule = (
        "List a company as a competitor ONLY if its name appears in the text of a provided source, "
        "and put those source numbers in source_ids. Copy the name exactly as written there."
        if sources
        else "No sources are available, so `competitors` MUST be an empty list. Describe alternatives generically "
        "(e.g. 'spreadsheets', 'general-purpose CRM tools') without naming companies."
    )
    return f"""You are the Competitor Agent in a team of startup analysts.
Map the competitive landscape for a startup idea: direct competitors, how customers cope today,
where the idea could differentiate, and gaps nobody serves well.

{grounding_rules(sources)}

Competitor rules:
- {competitor_rule}
- Strengths and weaknesses must come from the sources (with [n]) or be prefixed with "Likely:" when inferred.
- Never invent pricing, funding, customer counts, or market share."""


def _mentions(name: str, source: Source) -> bool:
    pattern = r"(?<!\w)" + re.escape(name.strip().lower()) + r"(?!\w)"
    return re.search(pattern, f"{source.title} {source.snippet}".lower()) is not None


def verify_competitors(analysis: CompetitorAnalysis, sources: list[Source]) -> CompetitorAnalysis:
    by_id = {s.id: s for s in sources}
    kept, dropped = [], list(analysis.unverified_competitors)
    for comp in analysis.competitors:
        if not comp.name.strip():
            continue
        supporting = [i for i in dict.fromkeys(comp.source_ids) if i in by_id and _mentions(comp.name, by_id[i])]
        if supporting:
            kept.append(comp.model_copy(update={"source_ids": supporting}))
        else:
            dropped.append(comp.name)
    return analysis.model_copy(update={"competitors": kept, "unverified_competitors": dropped})


async def run_competitor_agent(
    llm: BaseChatModel,
    req: StartupIdeaRequest,
    research: ResearchFindings,
    sources: list[Source],
) -> CompetitorAnalysis:
    human = (
        f"{format_idea(req)}\n\n"
        f"Research Agent findings (JSON):\n{research.model_dump_json(indent=2)}\n\n"
        f"{format_sources(sources, SNIPPET_CHARS)}"
    )
    analysis = await ask(llm, CompetitorAnalysis, system_prompt(sources), human)
    analysis = analysis.model_copy(update={"unverified_competitors": []})
    analysis, _ = clean_model(analysis, sources)
    return verify_competitors(analysis, sources)
