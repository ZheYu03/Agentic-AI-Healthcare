from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration pulled from environment or .env."""

    langchain_tracing_v2: bool = Field(default=True, alias="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field(alias="LANGCHAIN_ENDPOINT")
    langchain_api_key: str = Field(alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(alias="LANGCHAIN_PROJECT")

    pinecone_api_key: str = Field(alias="PINECONE_API_KEY")
    pinecone_environment: str = Field(alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(alias="PINECONE_INDEX_NAME")
    vector_store_mode: str = Field(default="cloud", alias="VECTOR_STORE_MODE")

    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_anon_key: str = Field(alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(alias="DATABASE_URL")

    gemini_api_key: str = Field(alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="GEMINI_MODEL", alias="GEMINI_MODEL")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def get_settings() -> Settings:
    """Return validated settings."""
    return Settings()
