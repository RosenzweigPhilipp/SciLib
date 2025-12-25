from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import secrets
import time
from .config import settings
from .auth import verify_session_token
from .api import papers, collections, tags
from .ai import endpoints as ai_endpoints

# Session storage (in production, use Redis or database)
active_sessions = {}

class LoginRequest(BaseModel):
    api_key: str

class LoginResponse(BaseModel):
    session_token: str
    expires_in: int

# Create FastAPI app
app = FastAPI(
    title="SciLib API",
    description="AI-powered scientific literature manager",
    version="1.0.0",
    debug=settings.debug
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes with authentication
app.include_router(papers.router, prefix="/api", dependencies=[Depends(verify_session_token)])
app.include_router(collections.router, prefix="/api", dependencies=[Depends(verify_session_token)])
app.include_router(tags.router, prefix="/api", dependencies=[Depends(verify_session_token)])
app.include_router(ai_endpoints.router, dependencies=[Depends(verify_session_token)])

# Public endpoints (no auth required)
@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("static/index.html")


@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login endpoint that exchanges API key for session token"""
    if request.api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Generate session token
    session_token = secrets.token_urlsafe(32)
    expires_at = time.time() + 86400  # 24 hours
    
    active_sessions[session_token] = {
        "expires_at": expires_at,
        "created_at": time.time()
    }
    
    return LoginResponse(
        session_token=session_token,
        expires_in=86400
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "SciLib API is running"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint - no auth required"""
    from .database import SessionLocal
    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy", 
        "message": "SciLib API is running",
        "database": db_status
    }


@app.get("/api/stats")
async def get_stats():
    """Get basic statistics - no auth required for demo"""
    from .database import SessionLocal, Paper, Collection, Tag
    from datetime import datetime, timedelta
    
    try:
        db = SessionLocal()
        
        # Count papers
        total_papers = db.query(Paper).count()
        
        # Count collections
        total_collections = db.query(Collection).count()
        
        # Count tags
        total_tags = db.query(Tag).count()
        
        # Count recent uploads (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_uploads = db.query(Paper).filter(Paper.created_at > thirty_days_ago).count()
        
        db.close()
        
        return {
            "total_papers": total_papers,
            "total_collections": total_collections, 
            "total_tags": total_tags,
            "recent_uploads": recent_uploads
        }
        
    except Exception as e:
        return {
            "total_papers": 0,
            "total_collections": 0,
            "total_tags": 0,
            "recent_uploads": 0,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)