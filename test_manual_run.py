#!/usr/bin/env python3
"""
Manual Test Script - Process a small batch of PDFs
Run this locally to test before deploying to cloud
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

# Import modules
from src.scraper import download_borderaux
from src.claude import ClaudeClient
from src.storage import get_storage_client
from src.database import get_database_client
from src.utils import setup_logging

logger = setup_logging()


def test_manual_run(
    year: int = 2025,
    competition: str = "142",  # Brasileiro Série A
    max_pdfs: int = 3  # Process only 3 PDFs for testing
):
    """
    Test run with limited scope.

    Args:
        year: Year to process
        competition: Competition code (142 = Brasileiro A, 424 = Copa do Brasil)
        max_pdfs: Maximum number of PDFs to process (for cost control)
    """
    logger.info("="*60)
    logger.info(f"MANUAL TEST RUN")
    logger.info(f"Year: {year}, Competition: {competition}, Max PDFs: {max_pdfs}")
    logger.info("="*60)

    # Initialize clients
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        logger.error("ANTHROPIC_API_KEY not found in environment!")
        return

    claude = ClaudeClient(api_key=anthropic_key)
    storage = get_storage_client()
    db = get_database_client()

    stats = {
        "pdfs_downloaded": 0,
        "pdfs_skipped_already_in_db": 0,
        "pdfs_skipped_already_in_storage": 0,
        "pdfs_processed": 0,
        "claude_api_calls": 0,
        "errors": 0
    }

    # Step 1: Download PDFs (limited to max_pdfs)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        logger.info(f"Step 1: Downloading PDFs to {temp_path}...")

        try:
            pdf_paths = download_borderaux(
                year=year,
                comp_code=competition,
                output_dir=temp_path,
                max_workers=1  # Single-threaded for testing
            )

            # Limit to max_pdfs
            pdf_paths = pdf_paths[:max_pdfs]
            stats["pdfs_downloaded"] = len(pdf_paths)

            logger.info(f"Downloaded {len(pdf_paths)} PDFs")

        except Exception as e:
            logger.error(f"Failed to download PDFs: {e}")
            return stats

        # Step 2: Process each PDF
        logger.info(f"\nStep 2: Processing PDFs...")

        for i, pdf_path in enumerate(pdf_paths, 1):
            id_jogo_cbf = pdf_path.stem

            logger.info(f"\n[{i}/{len(pdf_paths)}] Processing: {id_jogo_cbf}")

            try:
                # CHECK 1: Skip if already in database
                if db.match_exists(id_jogo_cbf):
                    logger.info(f"  ✓ SKIPPED - Already in database (no Claude API call!)")
                    stats["pdfs_skipped_already_in_db"] += 1
                    continue

                # CHECK 2: Try to upload PDF (will skip if already in storage)
                logger.info(f"  → Uploading PDF to Supabase Storage...")
                storage_path = storage.upload_pdf(
                    pdf_path=pdf_path,
                    year=year,
                    id_jogo_cbf=id_jogo_cbf,
                    overwrite=False  # Don't overwrite existing
                )

                if not storage_path:
                    logger.error(f"  ✗ Failed to upload PDF")
                    stats["errors"] += 1
                    continue

                # Check if it was actually uploaded or already existed
                # (storage.upload_pdf returns path even if file exists)

                # Step 3: Analyze with Claude ($$$ COSTS MONEY $$$)
                logger.info(f"  → Analyzing with Claude Haiku 4.5... ($$)")

                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                    file_size_mb = len(pdf_bytes) / 1024 / 1024
                    logger.info(f"     PDF size: {file_size_mb:.2f} MB")

                result = claude.analyze_pdf(pdf_bytes)
                stats["claude_api_calls"] += 1

                if not result.get("success"):
                    error = result.get("error", "Unknown error")
                    logger.error(f"  ✗ Claude analysis failed: {error}")
                    stats["errors"] += 1
                    continue

                # Step 4: Save to database
                logger.info(f"  → Saving to database...")

                # Extract match data
                data = result.get("data", {})
                match_data = {
                    "id_jogo_cbf": id_jogo_cbf,
                    "pdf_storage_path": storage_path,
                    "data_jogo": data.get("data_jogo"),
                    "competicao": data.get("competicao"),
                    "time_mandante": data.get("time_mandante"),
                    "time_visitante": data.get("time_visitante"),
                    "estadio": data.get("estadio"),
                    "cidade": data.get("cidade"),
                    "uf": data.get("uf"),
                    "placar_mandante": data.get("placar_mandante"),
                    "placar_visitante": data.get("placar_visitante"),
                    "receita_total": data.get("receita_total"),
                    "despesa_total": data.get("despesa_total"),
                    "saldo": data.get("saldo"),
                    "publico_total": data.get("publico_total"),
                    "publico_pagante": data.get("publico_pagante"),
                    "renda_liquida": data.get("renda_liquida"),
                }

                # Remove None values
                match_data = {k: v for k, v in match_data.items() if v is not None}

                success = db.add_match(match_data)

                if success:
                    logger.info(f"  ✓ SUCCESS - Processed and saved!")
                    stats["pdfs_processed"] += 1

                    # Add revenue/expense details if present
                    receitas = result.get("receitas", [])
                    if receitas:
                        db.add_revenue_details(id_jogo_cbf, receitas)

                    despesas = result.get("despesas", [])
                    if despesas:
                        db.add_expense_details(id_jogo_cbf, despesas)
                else:
                    logger.error(f"  ✗ Failed to save to database")
                    stats["errors"] += 1

            except Exception as e:
                logger.error(f"  ✗ Error processing {id_jogo_cbf}: {e}")
                stats["errors"] += 1

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST RUN COMPLETE")
    logger.info("="*60)
    logger.info(f"PDFs downloaded:              {stats['pdfs_downloaded']}")
    logger.info(f"PDFs skipped (in DB):         {stats['pdfs_skipped_already_in_db']}")
    logger.info(f"PDFs processed successfully:  {stats['pdfs_processed']}")
    logger.info(f"Claude API calls made:        {stats['claude_api_calls']}")
    logger.info(f"Errors:                       {stats['errors']}")
    logger.info("="*60)

    # Cost estimate
    if stats["claude_api_calls"] > 0:
        # Haiku 4.5 pricing (approximate):
        # Input: $0.80 per million tokens (~2,000 tokens per PDF)
        # Output: $4.00 per million tokens (~500 tokens per response)
        estimated_cost = stats["claude_api_calls"] * 0.01  # Rough estimate: $0.01 per PDF
        logger.info(f"\n💰 Estimated cost: ${estimated_cost:.2f} USD")
        logger.info(f"   (Rough estimate: ~$0.01 per PDF processed)")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manual test run with limited PDFs")
    parser.add_argument("--year", type=int, default=2025, help="Year to process")
    parser.add_argument("--competition", type=str, default="142",
                       help="Competition code (142=Brasileiro A, 424=Copa do Brasil)")
    parser.add_argument("--max-pdfs", type=int, default=3,
                       help="Maximum PDFs to process (for cost control)")

    args = parser.parse_args()

    stats = test_manual_run(
        year=args.year,
        competition=args.competition,
        max_pdfs=args.max_pdfs
    )
