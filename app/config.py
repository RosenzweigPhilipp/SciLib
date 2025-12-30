from pydantic_settings import BaseSettings
from typing import Optional
import os
import sys


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
        extra = "ignore"  # Ignore extra environment variables
    
    def validate_required_settings(self):
        """Validate that critical settings are properly configured."""
        errors = []
        
        # Check database URL is not default
        if self.database_url == "postgresql://username:password@localhost/scilib":
            errors.append("DATABASE_URL is not configured. Update .env file with your database connection.")
        
        # Check API key is not default
        if self.api_key == "your-secret-api-key-here":
            errors.append("API_KEY is not configured. Update .env file with a secure API key.")
        
        # Warn if OpenAI key is missing (not fatal, but AI features won't work)
        if not self.openai_api_key:
            print("⚠️  WARNING: OPENAI_API_KEY not set. AI extraction features will be limited.", file=sys.stderr)
        
        # Check upload directory is writable
        if not os.path.exists(self.upload_dir):
            try:
                os.makedirs(self.upload_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create upload directory {self.upload_dir}: {e}")
        elif not os.access(self.upload_dir, os.W_OK):
            errors.append(f"Upload directory {self.upload_dir} is not writable.")
        
        if errors:
            print("❌ Configuration Errors:", file=sys.stderr)
            for error in errors:
                print(f"   - {error}", file=sys.stderr)
            sys.exit(1)


settings = Settings()

# Validate settings at import time
if __name__ != "__main__":  # Don't validate during direct script execution
    settings.validate_required_settings()