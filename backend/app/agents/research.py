from langchain_core.language_models.chat_models import BaseChatModel

from app.agents.common import ask, format_idea, format_sources, grounding_rules
from app.schemas import ResearchFindings, Source, StartupIdeaRequest


def system_prompt(sources: list[Source]) -> str:
    return f"""You are the Research Agent in a team of startup analysts.
Analyze the market context for a startup idea: who the customers are, what pain they have,
which trends matter, and what could go wrong.

{grounding_rules(sources)}

Be specific to the idea and avoid generic filler. Each list should have 3-6 concise items."""


async def run_research_agent(
    llm: BaseChatModel, req: StartupIdeaRequest, sources: list[Source] | None = None
) -> ResearchFindings:
    sources = sources or []
    human = f"{format_idea(req)}\n\n{format_sources(sources)}"
    return await ask(llm, ResearchFindings, system_prompt(sources), human)
