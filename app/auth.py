from fastapi import HTTPException, status, Header
from typing import Optional
from .config import settings


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Verify API key authentication via X-API-Key header
    """
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Use X-API-Key header."
        )
    return x_api_key