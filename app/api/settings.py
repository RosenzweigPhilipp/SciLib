"""
API endpoints for application settings.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..database.models import Settings
from ..auth import verify_api_key

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(verify_api_key)])


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("/summaries/status")
async def get_summaries_status(db: Session = Depends(get_db)):
    """Get the current status of auto-summaries feature."""
    enabled = Settings.get(db, "summaries_auto_enabled", False)
    
    return {
        "enabled": enabled,
        "feature": "auto_summaries"
    }


@router.post("/summaries/toggle")
async def toggle_summaries(
    request: ToggleRequest,
    db: Session = Depends(get_db)
):
    """Toggle auto-summaries feature on or off."""
    Settings.set(db, "summaries_auto_enabled", request.enabled)
    
    return {
        "enabled": request.enabled,
        "message": f"Auto-summaries {'enabled' if request.enabled else 'disabled'}"
    }
