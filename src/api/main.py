"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from src.api.routes import analytics, pdfs, admin

app = FastAPI(
    title="CBF Borderô Robot API",
    description="API for Brazilian football match financial analysis",
    version="2.0.0"
)

# Configure CORS
# For Railway, allow all origins in development, specific in production
cors_origins = os.getenv("CORS_ORIGINS", "*")
if cors_origins == "*":
    origins = ["*"]
else:
    origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(pdfs.router, prefix="/api/pdfs", tags=["PDFs"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# Serve static files from frontend build (for Railway deployment)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount static files (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend for all routes except API and docs"""
        # Don't serve frontend for API or docs routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return {"error": "Not found"}, 404

        # Serve index.html for all other routes (React Router handles routing)
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        else:
            return {"error": "Frontend not built. Run 'cd frontend && npm run build'"}, 500
else:
    # Frontend not built - only API available
    @app.get("/")
    async def root():
        return {
            "message": "CBF Borderô Robot API",
            "version": "2.0.0",
            "docs": "/docs",
            "note": "Frontend not available. Build it with: cd frontend && npm run build"
        }

@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "CBF Borderô Robot API",
        "version": "2.0.0",
        "endpoints": {
            "analytics": "/api/analytics",
            "pdfs": "/api/pdfs",
            "admin": "/api/admin"
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    from src.database import SupabaseDatabase

    try:
        db = SupabaseDatabase()
        # Try a simple query
        db.client.table("jogos_resumo").select("id_jogo_cbf").limit(1).execute()
        return {
            "status": "healthy",
            "database": "connected",
            "frontend": "available" if frontend_dist.exists() else "not_built"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
