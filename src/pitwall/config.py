"""Central settings, loaded from environment variables / .env."""

from functools import lru_cache

from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # "KEY=" in .env is treated as unset
        extra="ignore",
    )

    # Postgres (admin: setup and migrations only)
    postgres_user: str = "pitwall_admin"
    postgres_password: SecretStr = SecretStr("change_me_admin")
    postgres_db: str = "pitwall"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Postgres (least-privilege roles; names must match migrations/002)
    agent_user: str = "pitwall_agent"
    agent_password: SecretStr = SecretStr("change_me_agent")
    publisher_user: str = "pitwall_publisher"
    publisher_password: SecretStr = SecretStr("change_me_publisher")

    # LLM providers (free tiers)
    google_api_key: SecretStr | None = None  # Gemini via Google AI Studio
    groq_api_key: SecretStr | None = None  # Groq, used for the judge
    gemini_model: str = "gemini-3.8-flash"
    groq_judge_model: str = "openai/gpt-oss-120b"

    # Local models (no key; used from the retrieval step)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # LangSmith
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "pitwall"

    def _conninfo(self, user: str, password: SecretStr) -> str:
        """libpq conninfo string; make_conninfo handles quoting of special characters."""
        return make_conninfo(
            host=self.postgres_host,
            port=self.postgres_port,
            dbname=self.postgres_db,
            user=user,
            password=password.get_secret_value(),
        )

    def admin_conninfo(self) -> str:
        return self._conninfo(self.postgres_user, self.postgres_password)

    def agent_conninfo(self) -> str:
        return self._conninfo(self.agent_user, self.agent_password)

    def publisher_conninfo(self) -> str:
        return self._conninfo(self.publisher_user, self.publisher_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()