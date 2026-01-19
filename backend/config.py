"""
Configuration settings for Finance Tracker
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
import os

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Finance Tracker"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{Path(__file__).parent.parent / 'data' / 'finance.db'}")

    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Authentication
    AUTH_USERNAME: Optional[str] = os.getenv("AUTH_USERNAME")
    AUTH_PASSWORD: Optional[str] = os.getenv("AUTH_PASSWORD")

    @property
    def AUTH_ENABLED(self) -> bool:
        """Auth is enabled when both username and password are set"""
        return bool(self.AUTH_USERNAME and self.AUTH_PASSWORD)

    # CORS Origins - parse from env or use defaults
    @property
    def CORS_ORIGINS(self) -> list:
        env_origins = os.getenv("CORS_ORIGINS", "")
        if env_origins:
            return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
        # Default development origins
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
