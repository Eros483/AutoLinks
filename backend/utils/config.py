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
    pioneer_api_key: str = ""
    qdrant_api_key: str = ""
    qdrant_url: str = "http://localhost:6333"

    # Application
    app_name: str = "AutoLinks"
    debug: bool = False
    dry_run: bool = False

    # GLiNER
    gliner_url: str = "https://api.pioneer.ai/v1/chat/completions"

    # Groq Judge
    groq_api_key: str = ""
    groq_url: str = "https://api.groq.com/openai/v1/chat/completions"
    groq_model: str = "llama-3.3-70b-versatile"

    # Qdrant
    qdrant_collection: str = "articles"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"

    # Re-ranking
    rerank_alpha: float = 0.7


config = Settings()
