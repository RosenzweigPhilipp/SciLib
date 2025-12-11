from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Simple test app without database
app = FastAPI(
    title="SciLib API",
    description="AI-powered scientific literature manager",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "SciLib API is running"}

@app.get("/api/papers")
async def list_papers():
    """Mock papers endpoint"""
    return []

@app.get("/api/collections")  
async def list_collections():
    """Mock collections endpoint"""
    return []

@app.get("/api/tags")
async def list_tags():
    """Mock tags endpoint"""
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)