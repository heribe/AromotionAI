"""
AromotionAI Global Configuration module.

R2 Three-Question Self-Check:
1. Contract Closure: Type safety is guaranteed by Pydantic Settings. Fallback defaults are provided for all fields.
2. Symmetry: Singletone settings object, no active resources required to release.
3. External Timing: Read-only load during startup, thread-safe.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Git Worktree compatibility: resolve path dynamically relative to file location
_BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BASE_DIR / ".env"

class Settings(BaseSettings):
    APP_NAME: str = "AromotionAI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "development-only-insecure-secret"
    
    DATABASE_URL: str = "sqlite:///./data/db/aromotion.db"
    
    STORAGE_TYPE: str = "local"
    STORAGE_LOCAL_PATH: str = "./data/media"
    
    GLM_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    
    CORS_ORIGINS: str = "http://localhost:5173"
    COOKIE_DIR: str = "./data/cookies"

    @property
    def BASE_DIR(self) -> Path:
        return _BASE_DIR

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
