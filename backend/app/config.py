"""
Hybrid Quantum-AI Drug Discovery Platform — Backend
Configuration settings loaded from environment variables.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Hybrid Quantum-AI Drug Discovery Platform"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./hybrid_drug_discovery.db"

    # Authentication
    secret_key: str = "change-this-to-a-strong-random-secret-key-before-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # File paths (relative to backend root)
    data_raw_path: str = "../data/raw"
    data_processed_path: str = "../data/processed"
    models_path: str = "../models"
    reports_path: str = "../reports"

    # Redis / Celery (for later milestones)
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Frontend
    frontend_url: str = "http://localhost:5173"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
