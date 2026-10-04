import os
from typing import List, Union, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "GrantCheck — AI Funding Application Review Workbench"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: Union[bool, str] = True
    LOG_LEVEL: str = "INFO"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> Any:
        if isinstance(v, str):
            if v.lower() in ("true", "1", "yes", "on", "t"):
                return True
            if v.lower() in ("false", "0", "no", "off", "f"):
                return False
            return v
        return v

    # Regulatory Disclaimer
    REGULATORY_DISCLAIMER: str = (
        "GrantCheck is an AI-assisted completeness and evidence-review workbench. "
        "It does NOT make an authoritative legal, regulatory, or funding-eligibility decision. "
        "All funding decisions must be made by qualified human authorities."
    )

    # Database
    DATABASE_URL: str = "sqlite:///./grantcheck.db"

    # LLM Provider: 'mock', 'openai', 'gemini'
    LLM_PROVIDER: str = "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 3

    # Uploads
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    MAX_UPLOAD_SIZE_MB: int = 25

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
