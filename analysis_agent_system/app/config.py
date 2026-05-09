"""Application configuration."""
import os
from pathlib import Path
from urllib.parse import quote

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, continue with system environment variables
    pass


class Settings:
    APP_TITLE: str = "Analysis Agent System API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Analysis Agent System RESTful API based on the interface design specification."
    
    # Application Settings
    HOST: str = os.getenv("APP_HOST", "") or "0.0.0.0"
    PORT: int = int(os.getenv("APP_PORT", "") or "8000")
    DEBUG: bool = (os.getenv("APP_DEBUG", "") or "true").lower() == "true"
    
    # File upload
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "") or "./uploads"
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "") or "500")
    
    # File export
    EXPORT_DIR: str = os.getenv("EXPORT_DIR", "") or "./exports"
    
    # Auth (placeholder)
    AUTH_SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", "") or "change-me-in-production"

    # ------------------------------------------------------------------
    # LLM (VLLM) Configuration
    # ------------------------------------------------------------------
    VLLM_API_BASE: str = os.getenv("VLLM_API_BASE", "") or "http://localhost:8080/v1"
    VLLM_API_KEY: str = os.getenv("VLLM_API_KEY", "") or "EMPTY"
    MODEL_NAME: str = os.getenv("MODEL_NAME", "") or "qwen3-vl-8b-instruct"
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "") or "4096")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "") or "0.7")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "") or "120")  # seconds

    # ------------------------------------------------------------------
    # Database Configuration
    # ------------------------------------------------------------------
    DB_HOST: str = os.getenv("DB_HOST", "") or "localhost"
    DB_PORT: int = int(os.getenv("DB_PORT", "") or "3306")
    DB_NAME: str = os.getenv("DB_NAME", "") or "analysis"
    DB_USER: str = os.getenv("DB_USER", "") or "root"
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "") or ""
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "") or "10")
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "") or "20")
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "") or "3600")

    @property
    def DATABASE_URL(self) -> str:
        """Build SQLAlchemy database URL."""
        # URL-encode credentials to handle special characters (@, #, :, etc.)
        safe_user = quote(self.DB_USER, safe="")
        safe_password = quote(self.DB_PASSWORD, safe="")
        return (
            f"mysql+pymysql://{safe_user}:{safe_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


settings = Settings()
