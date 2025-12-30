from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .config import settings
from .api import papers, collections, tags
from .ai import endpoints as ai_endpoints

# Simple API key authentication with debug logging
def verify_api_key(x_api_key: Optional[str] = Header(None)):
    print(f"DEBUG: Received API key: {x_api_key}")
    print(f"DEBUG: Expected API key: {settings.api_key}")
    if not x_api_key or x_api_key != settings.api_key:
        print(f"DEBUG: Authentication failed - key mismatch")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Use X-API-Key header."
        )
    print(f"DEBUG: Authentication successful")
    return x_api_key

# Create FastAPI app
app = FastAPI(
    title="SciLib API",
    description="AI-powered scientific literature manager",
    version="1.0.0",
    debug=settings.debug
)

# Configure CORS - restrict to localhost only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",  # For development frontends
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes with simple API key authentication
app.include_router(papers.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(collections.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(tags.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(ai_endpoints.router, dependencies=[Depends(verify_api_key)])

# Public endpoints (no auth required)
@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("static/index.html")


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
        with SessionLocal() as db:
            db.execute("SELECT 1")
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
        with SessionLocal() as db:
            # Count papers
            total_papers = db.query(Paper).count()
            
            # Count collections
            total_collections = db.query(Collection).count()
            
            # Count tags
            total_tags = db.query(Tag).count()
            
            # Count recent uploads (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_uploads = db.query(Paper).filter(Paper.created_at > thirty_days_ago).count()
        
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