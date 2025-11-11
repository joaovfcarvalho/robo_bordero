"""
Admin API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional
import asyncio
from datetime import datetime

from src.api.models import (
    LoginRequest,
    LoginResponse,
    BulkScrapeRequest,
    BulkScrapeResponse,
)
from src.api.auth import verify_admin_password, generate_token, get_current_user

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """Admin login endpoint"""
    if not verify_admin_password(request.password):
        return LoginResponse(
            success=False,
            message="Invalid password",
        )

    token = generate_token()
    return LoginResponse(
        success=True,
        token=token,
        message="Login successful",
    )


@router.post("/logout", dependencies=[Depends(get_current_user)])
async def admin_logout(token: str = Depends(get_current_user)):
    """Admin logout endpoint"""
    from src.api.auth import _active_tokens

    if token in _active_tokens:
        del _active_tokens[token]

    return {"success": True, "message": "Logged out successfully"}


async def run_bulk_scrape_task(year: int, competition_codes: Optional[list], force_reprocess: bool):
    """Background task for bulk scraping"""
    from src.cloud_worker import CloudWorker

    worker = CloudWorker()

    try:
        # If no competition codes provided, use defaults
        if not competition_codes:
            competition_codes = ["142", "424", "242"]

        # Run scrape and process
        results = await asyncio.to_thread(
            worker.scrape_and_process,
            year=year,
            competitions=competition_codes,
        )

        print(f"Bulk scrape completed: {results}")

    except Exception as e:
        print(f"Error in bulk scrape: {str(e)}")


@router.post("/bulk-scrape", response_model=BulkScrapeResponse, dependencies=[Depends(get_current_user)])
async def bulk_scrape(request: BulkScrapeRequest, background_tasks: BackgroundTasks):
    """
    Start bulk scraping for a year and competition(s)
    This will download all PDFs and process them
    """
    try:
        # Validate year
        current_year = datetime.now().year
        if request.year < 2020 or request.year > current_year + 1:
            raise HTTPException(status_code=400, detail="Invalid year")

        # Generate job ID
        job_id = f"bulk-{request.year}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Estimate number of PDFs (rough estimate)
        competition_count = len(request.competition_codes) if request.competition_codes else 3
        estimated_pdfs = competition_count * 50  # Rough estimate

        # Start background task
        background_tasks.add_task(
            run_bulk_scrape_task,
            request.year,
            request.competition_codes,
            request.force_reprocess,
        )

        return BulkScrapeResponse(
            success=True,
            message=f"Bulk scrape started for year {request.year}",
            job_id=job_id,
            estimated_pdfs=estimated_pdfs,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting bulk scrape: {str(e)}")


@router.get("/stats", dependencies=[Depends(get_current_user)])
async def get_admin_stats():
    """Get admin statistics"""
    from src.database import SupabaseDatabase
    from src.storage import SupabaseStorage

    try:
        db = SupabaseDatabase()
        storage = SupabaseStorage()

        # Count matches
        matches_response = db.client.table("jogos_resumo").select("id_jogo_cbf", count="exact").execute()
        total_matches = matches_response.count if hasattr(matches_response, 'count') else len(matches_response.data)

        # Count queue items
        queue_response = db.client.table("processing_queue").select("id_jogo_cbf,status", count="exact").execute()
        total_queue = queue_response.count if hasattr(queue_response, 'count') else len(queue_response.data)

        # Count by status
        queue_items = queue_response.data
        pending_count = len([q for q in queue_items if q.get('status') == 'pending'])
        processing_count = len([q for q in queue_items if q.get('status') == 'processing'])
        failed_count = len([q for q in queue_items if q.get('status') == 'failed'])

        # Get storage info (PDFs)
        try:
            pdfs_2024 = storage.list_pdfs(2024)
            pdfs_2025 = storage.list_pdfs(2025)
            total_pdfs_stored = len(pdfs_2024) + len(pdfs_2025)
        except:
            total_pdfs_stored = 0

        return {
            "total_matches": total_matches,
            "total_queue_items": total_queue,
            "queue_pending": pending_count,
            "queue_processing": processing_count,
            "queue_failed": failed_count,
            "pdfs_stored": total_pdfs_stored,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.post("/refresh-normalizations", dependencies=[Depends(get_current_user)])
async def refresh_normalizations(background_tasks: BackgroundTasks):
    """Refresh name normalizations for teams, stadiums, and competitions"""
    from src.cloud_worker import CloudWorker

    try:
        worker = CloudWorker()

        # Run in background
        background_tasks.add_task(worker._refresh_normalizations)

        return {
            "success": True,
            "message": "Normalization refresh started",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting normalization refresh: {str(e)}")


@router.delete("/matches/{id_jogo_cbf}", dependencies=[Depends(get_current_user)])
async def delete_match(id_jogo_cbf: str):
    """Delete a match and all related data"""
    from src.database import SupabaseDatabase

    try:
        db = SupabaseDatabase()

        success = db.delete_match(id_jogo_cbf)

        if not success:
            raise HTTPException(status_code=404, detail="Match not found")

        return {
            "success": True,
            "message": f"Match {id_jogo_cbf} deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting match: {str(e)}")
