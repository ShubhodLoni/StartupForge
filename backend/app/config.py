from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_temperature: float = 0.2

    tavily_api_key: str = ""
    search_queries: int = 3
    competitor_queries: int = 2
    search_max_results: int = 3
    source_snippet_chars: int = 600

    database_url: str = ""

    rag_enabled: bool = True
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    rag_top_k: int = 6
    chunk_size: int = 800
    chunk_overlap: int = 120
    max_page_chars: int = 8000

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
