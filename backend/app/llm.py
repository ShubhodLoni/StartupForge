from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings


class LLMNotConfiguredError(RuntimeError):
    pass


def build_llm(settings: Settings) -> BaseChatModel:
    if not settings.groq_api_key:
        raise LLMNotConfiguredError(
            "GROQ_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    from langchain_groq import ChatGroq

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.groq_temperature,
        max_retries=4,
    )
