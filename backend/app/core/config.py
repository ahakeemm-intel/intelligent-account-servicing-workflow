from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Literal
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../../../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Running mode
    APP_MODE: Literal["local", "cloud", "docker"] = "local"

    # LLM
    LLM_PROVIDER: Literal["ollama", "openai"] = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_VISION_MODEL: str = "llava"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # OCR
    OCR_PROVIDER: Literal["tesseract", "textract"] = "tesseract"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"

    # Database
    DB_TYPE: Literal["sqlite", "postgres"] = "sqlite"
    SQLITE_PATH: str = "./data/iasw.db"
    DATABASE_URL: str = "postgresql+asyncpg://iasw:iasw@localhost:5432/iasw"

    # Confidence thresholds
    CONFIDENCE_PASS_THRESHOLD: float = 0.90
    CONFIDENCE_FLAG_THRESHOLD: float = 0.60

    # Observability
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/iasw.log"
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # FileNet mock
    FILENET_STORE_PATH: str = "./filenet_store"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    def get_db_url(self) -> str:
        """Return the appropriate DB URL based on DB_TYPE."""
        if self.DB_TYPE == "sqlite":
            # Resolve relative path from the backend/ working dir
            path = self.SQLITE_PATH
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(__file__), "../../../..", path)
                path = os.path.normpath(path)
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return f"sqlite+aiosqlite:///{path}"
        return self.DATABASE_URL


settings = Settings()
