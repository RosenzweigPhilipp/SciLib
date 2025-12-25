from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://username:password@localhost/scilib"
    
    # API
    api_key: str = "your-secret-api-key-here"
    openai_api_key: Optional[str] = None
    debug: bool = True
    
    # AI Services
    langchain_api_key: Optional[str] = None
    langsmith_api_key: Optional[str] = None
    exa_api_key: Optional[str] = None
    
    # Scientific APIs
    crossref_email: Optional[str] = None
    semantic_scholar_api_key: Optional[str] = None
    
    # Background Processing
    redis_url: str = "redis://localhost:6379"
    celery_broker_url: str = "redis://localhost:6379"
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    
    # File Upload
    upload_dir: str = "./uploads"
    max_file_size: int = 50_000_000  # 50MB
    
    # PDF Processing
    max_ocr_pages: int = 10
    ocr_language: str = "eng"
    extraction_timeout: int = 300
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()