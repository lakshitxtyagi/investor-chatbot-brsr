"""
config.py — All configuration via environment variables (with sensible defaults).
Copy .env.example to .env and fill in secrets before running.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Weaviate
    WEAVIATE_HOST: str = "localhost"
    WEAVIATE_PORT: int = 8083
    WEAVIATE_GRPC_PORT: int = 50051
    WEAVIATE_API_KEY: str = "user-a-key"

    @property
    def WEAVIATE_URL(self) -> str:
        return f"http://{self.WEAVIATE_HOST}:{self.WEAVIATE_PORT}"

    # Embedding model (must match the one used during indexing)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_MODEL_PATH: str = os.path.join(os.path.dirname(__file__), "model")

    # Weaviate collections to search (must match schema class names)
    DEFAULT_COLLECTIONS: list[str] = ["NarrativeCollection", "NumericalCollection"]

    # OpenAI (primary LLM)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-5-mini-2025-08-07"

    # Groq (first fallback)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Gemini (second fallback)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.0-flash"


settings = Settings()
