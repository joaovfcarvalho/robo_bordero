"""
PDF Management API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Optional
import asyncio
from datetime import datetime, date

from src.database import SupabaseDatabase
from src.storage import SupabaseStorage
from src.scraper import download_pdfs
from src.claude import ClaudeClient
from src.api.models import (
    PDFInfo,
    ScrapeRequest,
    ScrapeResponse,
    QueueItem,
    QueueStatusResponse,
    QueueStatus,
)
from src.api.auth import get_current_user

router = APIRouter()


def generate_cbf_pdf_url(id_jogo_cbf: str, competition_code: str, year: int) -> str:
    """Generate CBF PDF URL from match ID"""
    # Extract the match number from the ID (e.g., "142-2025-001234" -> "001234")
    parts = id_jogo_cbf.split('-')
    if len(parts) >= 3:
        match_number = parts[2]
        # CBF URL pattern
        return f"https://conteudo.cbf.com.br/sumulas/{year}/{competition_code}_bordero_{match_number}.pdf"
    return ""


@router.get("/available", response_model=List[PDFInfo])
async def get_available_pdfs(
    year: Optional[int] = None,
    competition: Optional[str] = None,
    processed_only: bool = False,
    unprocessed_only: bool = False,
):
    """Get list of available PDFs/matches"""
    try:
        db = SupabaseDatabase()

        # Build query for processed matches
        query = db.client.table("jogos_resumo").select("id_jogo_cbf,competicao,data_jogo,time_mandante,time_visitante,processado_em,pdf_storage_path")

        if year:
            query = query.gte("data_jogo", f"{year}-01-01").lte("data_jogo", f"{year}-12-31")
        if competition:
            query = query.eq("competicao", competition)

        response = query.execute()
        processed_matches = {m['id_jogo_cbf']: m for m in response.data}

        # Get queue items (pending/processing)
        queue_query = db.client.table("processing_queue").select("*")
        if year:
            query = query.eq("ano", year)
        if competition:
            query = query.eq("competicao", competition)

        queue_response = queue_query.execute()
        queue_items = {q['id_jogo_cbf']: q for q in queue_response.data}

        # Combine both sources
        all_pdfs = []

        # Add processed matches
        for id_jogo, match in processed_matches.items():
            if unprocessed_only:
                continue

            # Extract year from date
            match_date = match.get('data_jogo')
            if match_date:
                match_year = int(match_date.split('-')[0])
            else:
                match_year = year or datetime.now().year

            # Generate PDF URL
            competition_code = id_jogo.split('-')[0] if '-' in id_jogo else ''
            pdf_url = generate_cbf_pdf_url(id_jogo, competition_code, match_year)

            all_pdfs.append(
                PDFInfo(
                    id_jogo_cbf=id_jogo,
                    competicao=match['competicao'],
                    ano=match_year,
                    time_mandante=match.get('time_mandante'),
                    time_visitante=match.get('time_visitante'),
                    data_jogo=datetime.fromisoformat(match_date).date() if match_date else None,
                    pdf_url=pdf_url,
                    processed=True,
                    processado_em=datetime.fromisoformat(match['processado_em']) if match.get('processado_em') else None,
                )
            )

        # Add queue items (not yet processed)
        for id_jogo, queue_item in queue_items.items():
            if id_jogo in processed_matches and not queue_item.get('status') == 'pending':
                continue  # Already included in processed

            if processed_only:
                continue

            all_pdfs.append(
                PDFInfo(
                    id_jogo_cbf=id_jogo,
                    competicao=queue_item['competicao'],
                    ano=queue_item['ano'],
                    pdf_url=queue_item['pdf_url'],
                    processed=False,
                    processado_em=None,
                )
            )

        return all_pdfs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching PDFs: {str(e)}")


@router.get("/queue", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get processing queue status"""
    try:
        db = SupabaseDatabase()

        # Get all queue items
        response = db.client.table("processing_queue").select("*").execute()
        items = response.data

        # Count by status
        status_counts = {
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
        }

        for item in items:
            status = item.get('status', 'pending')
            if status in status_counts:
                status_counts[status] += 1

        # Get recent items (last 20)
        recent_response = db.client.table("processing_queue").select("*").order("adicionado_em", desc=True).limit(20).execute()

        recent_items = [
            QueueItem(
                id_jogo_cbf=item['id_jogo_cbf'],
                pdf_url=item['pdf_url'],
                competicao=item['competicao'],
                ano=item['ano'],
                status=QueueStatus(item.get('status', 'pending')),
                tentativas=item.get('tentativas', 0),
                ultimo_erro=item.get('ultimo_erro'),
                adicionado_em=datetime.fromisoformat(item['adicionado_em']) if item.get('adicionado_em') else datetime.now(),
                processado_em=datetime.fromisoformat(item['processado_em']) if item.get('processado_em') else None,
            )
            for item in recent_response.data
        ]

        return QueueStatusResponse(
            total_pending=status_counts['pending'],
            total_processing=status_counts['processing'],
            total_completed=status_counts['completed'],
            total_failed=status_counts['failed'],
            recent_items=recent_items,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching queue status: {str(e)}")


async def process_pdf_task(id_jogo_cbf: str, pdf_url: str, competicao: str, ano: int, force_reprocess: bool = False):
    """Background task to process a PDF"""
    from src.cloud_worker import CloudWorker
    import tempfile
    import os
    import requests
    from pathlib import Path

    db = SupabaseDatabase()
    storage = SupabaseStorage()
    worker = CloudWorker()

    try:
        # Update queue status to processing
        db.update_queue_status(id_jogo_cbf, "processing", None)

        # Download PDF
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name

        try:
            # Process PDF - _process_pdf returns bool
            success = worker._process_pdf(Path(tmp_path), ano, id_jogo_cbf)

            if success:
                # Update queue status
                db.update_queue_status(id_jogo_cbf, "completed", None)
            else:
                error_msg = 'Processing failed - check logs for details'
                db.update_queue_status(id_jogo_cbf, "failed", error_msg)

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        error_msg = f"Error processing PDF: {str(e)}"
        db.update_queue_status(id_jogo_cbf, "failed", error_msg)


@router.post("/scrape", response_model=ScrapeResponse, dependencies=[Depends(get_current_user)])
async def scrape_pdf(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Force scrape a specific PDF (protected endpoint)"""
    try:
        db = SupabaseDatabase()

        # Check if already processed
        if not request.force_reprocess and db.match_exists(request.id_jogo_cbf):
            return ScrapeResponse(
                success=False,
                message="Match already processed. Use force_reprocess=true to reprocess.",
                id_jogo_cbf=request.id_jogo_cbf,
            )

        # Add to queue
        success = db.add_to_queue(
            id_jogo_cbf=request.id_jogo_cbf,
            pdf_url=request.pdf_url,
            competicao=request.competicao,
            ano=request.ano,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to add to processing queue")

        # Start background processing
        background_tasks.add_task(
            process_pdf_task,
            request.id_jogo_cbf,
            request.pdf_url,
            request.competicao,
            request.ano,
            request.force_reprocess,
        )

        return ScrapeResponse(
            success=True,
            message="PDF scraping started",
            id_jogo_cbf=request.id_jogo_cbf,
            job_id=request.id_jogo_cbf,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting scrape: {str(e)}")


@router.delete("/queue/{id_jogo_cbf}", dependencies=[Depends(get_current_user)])
async def remove_from_queue(id_jogo_cbf: str):
    """Remove item from processing queue"""
    try:
        db = SupabaseDatabase()

        response = db.client.table("processing_queue").delete().eq("id_jogo_cbf", id_jogo_cbf).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Queue item not found")

        return {"success": True, "message": "Item removed from queue"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing from queue: {str(e)}")


@router.post("/queue/retry/{id_jogo_cbf}", dependencies=[Depends(get_current_user)])
async def retry_failed_item(id_jogo_cbf: str, background_tasks: BackgroundTasks):
    """Retry a failed queue item"""
    try:
        db = SupabaseDatabase()

        # Get the queue item
        response = db.client.table("processing_queue").select("*").eq("id_jogo_cbf", id_jogo_cbf).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Queue item not found")

        item = response.data[0]

        # Reset status to pending
        db.update_queue_status(id_jogo_cbf, "pending", None)

        # Start background processing
        background_tasks.add_task(
            process_pdf_task,
            item['id_jogo_cbf'],
            item['pdf_url'],
            item['competicao'],
            item['ano'],
            False,
        )

        return {"success": True, "message": "Retry started"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrying item: {str(e)}")
