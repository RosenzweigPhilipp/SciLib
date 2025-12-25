from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://username:password@localhost/scilib"
    
    # API
    api_key: str = "your-secret-api-key-here"
    openai_api_key: Optional[str] = None
    debug: bool = True
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    
    # File Upload
    upload_dir: str = "./uploads"
    max_file_size: int = 50_000_000  # 50MB
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()