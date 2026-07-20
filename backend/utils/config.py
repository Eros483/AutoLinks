import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """
    Central management for settings and configurations
    Reads .env file
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API Keys
    qdrant_api_key: str = ""
    hf_token: str = ""
    groq_api_key: str = ""

    # URLs
    qdrant_url: str = "http://localhost:6333"
    models_space_url: str = ""
    groq_url: str = "https://api.groq.com/openai/v1/chat/completions"

    # Application
    app_name: str = "AutoLinks"
    debug: bool = False
    dry_run: bool = False

    # Groq Judge
    groq_model: str = "llama-3.3-70b-versatile"

    # Qdrant
    qdrant_collection: str = "articles"

    # Embedding (dev fallback only; production uses HF Space)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Re-ranking
    rerank_alpha: float = 0.7

    # Async Ingestion (Redis + Celery)
    redis_url: str = ""


config = Settings()
