from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .config import settings
from .auth import verify_api_key
from .api import papers, collections, tags

# Create FastAPI app
app = FastAPI(
    title="SciLib API",
    description="AI-powered scientific literature manager",
    version="1.0.0",
    debug=settings.debug
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(papers.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(collections.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(tags.router, prefix="/api", dependencies=[Depends(verify_api_key)])


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "SciLib API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)