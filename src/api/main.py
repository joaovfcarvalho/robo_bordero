"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from pathlib import Path

# Configure logging for startup debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting CBF Borderô Robot API...")

from src.api.routes import analytics, pdfs, admin

logger.info("API routes imported successfully")

app = FastAPI(
    title="CBF Borderô Robot API",
    description="API for Brazilian football match financial analysis",
    version="2.0.0"
)

# Configure CORS
# Allow Vercel frontend and development origins
cors_origins = os.getenv("CORS_ORIGINS", "*")
if cors_origins == "*":
    # Development mode - allow all origins
    origins = ["*"]
else:
    # Production mode - parse comma-separated origins
    # Example: https://your-frontend.vercel.app,https://www.your-domain.com
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
assets_dir = frontend_dist / "assets"

logger.info(f"Checking frontend build at: {frontend_dist}")
logger.info(f"Frontend dist exists: {frontend_dist.exists()}")
logger.info(f"Assets dir exists: {assets_dir.exists()}")

if frontend_dist.exists() and assets_dir.exists():
    # Mount static files (JS, CSS, images, etc.)
    logger.info(f"Mounting static assets from: {assets_dir}")
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    logger.info("Static assets mounted successfully")

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
    logger.warning(f"Frontend not available - dist: {frontend_dist.exists()}, assets: {assets_dir.exists()}")
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

    response = {
        "status": "healthy",
        "frontend": "available" if frontend_dist.exists() else "not_built"
    }

    try:
        db = SupabaseDatabase()
        # Try a simple query
        db.client.table("jogos_resumo").select("id_jogo_cbf").limit(1).execute()
        response["database"] = "connected"
    except ValueError as e:
        # Missing credentials - expected during initial deployment
        response["database"] = "not_configured"
        response["database_note"] = "Supabase credentials not set"
    except Exception as e:
        # Other errors - log but don't fail health check
        response["database"] = "error"
        response["database_error"] = str(e)

    return response

logger.info("FastAPI application initialized successfully")
logger.info(f"Application ready - Frontend available: {frontend_dist.exists()}")
