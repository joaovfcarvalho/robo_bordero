"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from src.api.routes import analytics, pdfs, admin

app = FastAPI(
    title="CBF Borderô Robot API",
    description="API for Brazilian football match financial analysis",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(pdfs.router, prefix="/api/pdfs", tags=["PDFs"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

@app.get("/")
async def root():
    return {
        "message": "CBF Borderô Robot API",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from src.database import SupabaseDatabase

    try:
        db = SupabaseDatabase()
        # Try a simple query
        db.client.table("jogos_resumo").select("id_jogo_cbf").limit(1).execute()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
