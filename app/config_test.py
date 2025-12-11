from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./scilib.db"  # Use SQLite for testing
    
    # API
    api_key: str = "scilib-demo-key-2024"
    debug: bool = True
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File Upload
    upload_dir: str = "./uploads"
    max_file_size: int = 50_000_000  # 50MB
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()