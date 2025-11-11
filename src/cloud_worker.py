"""
Cloud Worker for CBF Robot.
Replaces the Tkinter GUI for cloud deployment.
Runs scheduled scraping and processing jobs.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime, date
import tempfile
import structlog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import CBF Robot modules
from src.scraper import download_borderaux
from src.claude import ClaudeClient
from src.storage import get_storage_client
from src.database import get_database_client
from src.utils import setup_logging
from src.normalize import refresh_lookups

logger = setup_logging()


class CloudWorker:
    """
    Cloud-based worker for automated CBF borderô processing.

    This replaces the Tkinter GUI and runs as a scheduled job.
    """

    def __init__(self):
        """Initialize cloud worker with required clients."""
        logger.info("Initializing Cloud Worker")

        # Get API keys from environment
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        # Initialize clients
        self.claude = ClaudeClient(api_key=self.anthropic_key)
        self.storage = get_storage_client()
        self.db = get_database_client()

        # Configuration
        self.current_year = date.today().year
        self.competitions = self._get_competitions_config()

        logger.info(
            "Cloud Worker initialized",
            year=self.current_year,
            competitions=len(self.competitions)
        )

    def _get_competitions_config(self) -> List[str]:
        """
        Get competition codes from environment or use defaults.

        Returns:
            List of competition codes
        """
        # Default competitions
        defaults = [
            "142",  # Brasileiro Série A
            "424",  # Copa do Brasil
            "242",  # Brasileiro Série B
        ]

        # Allow override via env var (comma-separated)
        env_comps = os.getenv("CBF_COMPETITIONS")
        if env_comps:
            return [c.strip() for c in env_comps.split(",")]

        return defaults

    def scrape_and_process(self, year: Optional[int] = None) -> Dict[str, int]:
        """
        Main job: Scrape PDFs and process them with Claude.

        Args:
            year: Year to process (defaults to current year)

        Returns:
            Dict with job statistics
        """
        year = year or self.current_year

        logger.info("=" * 60)
        logger.info(f"Starting scrape and process job for {year}")
        logger.info("=" * 60)

        stats = {
            "pdfs_downloaded": 0,
            "pdfs_processed": 0,
            "pdfs_skipped": 0,
            "errors": 0
        }

        # Use temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Process each competition
            for comp_code in self.competitions:
                logger.info(f"Processing competition: {comp_code}")

                try:
                    # Step 1: Download PDFs
                    pdf_paths = self._download_pdfs(year, comp_code, temp_path)
                    stats["pdfs_downloaded"] += len(pdf_paths)

                    # Step 2: Process each PDF
                    for pdf_path in pdf_paths:
                        try:
                            id_jogo_cbf = pdf_path.stem  # Filename without .pdf

                            # Check if already processed
                            if self.db.match_exists(id_jogo_cbf):
                                logger.debug(f"Skipping already processed: {id_jogo_cbf}")
                                stats["pdfs_skipped"] += 1
                                continue

                            # Process PDF
                            success = self._process_pdf(pdf_path, year, id_jogo_cbf)

                            if success:
                                stats["pdfs_processed"] += 1
                            else:
                                stats["errors"] += 1

                        except Exception as e:
                            logger.error(f"Error processing {pdf_path}: {e}")
                            stats["errors"] += 1

                except Exception as e:
                    logger.error(f"Error processing competition {comp_code}: {e}")
                    stats["errors"] += 1

        # Step 3: Refresh normalization lookups
        logger.info("Refreshing normalization lookups...")
        self._refresh_normalizations()

        logger.info("=" * 60)
        logger.info("Job completed", **stats)
        logger.info("=" * 60)

        return stats

    def _download_pdfs(
        self,
        year: int,
        comp_code: str,
        download_dir: Path
    ) -> List[Path]:
        """
        Download PDFs for a competition.

        Args:
            year: Year
            comp_code: Competition code
            download_dir: Directory to save PDFs

        Returns:
            List of downloaded PDF paths
        """
        try:
            logger.info(f"Downloading PDFs: year={year}, competition={comp_code}")

            # Use the scraper module
            pdf_paths = download_borderaux(
                year=year,
                comp_code=comp_code,
                output_dir=download_dir,
                max_workers=5
            )

            logger.info(f"Downloaded {len(pdf_paths)} PDFs", competition=comp_code)
            return pdf_paths

        except Exception as e:
            logger.error(f"Failed to download PDFs: {e}", competition=comp_code)
            return []

    def _process_pdf(
        self,
        pdf_path: Path,
        year: int,
        id_jogo_cbf: str
    ) -> bool:
        """
        Process a single PDF with Claude and store in Supabase.

        Args:
            pdf_path: Path to PDF file
            year: Year of the match
            id_jogo_cbf: CBF match ID

        Returns:
            True if successful
        """
        try:
            logger.info(f"Processing PDF: {id_jogo_cbf}")

            # Step 1: Upload PDF to Supabase Storage
            storage_path = self.storage.upload_pdf(
                pdf_path=pdf_path,
                year=year,
                id_jogo_cbf=id_jogo_cbf
            )

            if not storage_path:
                logger.error(f"Failed to upload PDF: {id_jogo_cbf}")
                return False

            # Step 2: Analyze PDF with Claude
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            result = self.claude.analyze_pdf(pdf_bytes)

            if not result.get("success"):
                error = result.get("error", "Unknown error")
                logger.error(f"Claude analysis failed: {error}", id_jogo=id_jogo_cbf)
                return False

            # Step 3: Extract data from Claude response
            match_data = self._extract_match_data(result, id_jogo_cbf, storage_path)

            # Step 4: Save to database
            success = self.db.add_match(match_data)

            if not success:
                logger.error(f"Failed to save match to database: {id_jogo_cbf}")
                return False

            # Step 5: Save revenue/expense details if present
            receitas = result.get("receitas", [])
            if receitas:
                self.db.add_revenue_details(id_jogo_cbf, receitas)

            despesas = result.get("despesas", [])
            if despesas:
                self.db.add_expense_details(id_jogo_cbf, despesas)

            logger.info(f"Successfully processed: {id_jogo_cbf}")
            return True

        except Exception as e:
            logger.error(f"Error processing PDF: {e}", id_jogo=id_jogo_cbf)
            return False

    def _extract_match_data(
        self,
        claude_result: dict,
        id_jogo_cbf: str,
        storage_path: str
    ) -> dict:
        """
        Extract match data from Claude API response.

        Args:
            claude_result: Claude API response
            id_jogo_cbf: CBF match ID
            storage_path: Supabase Storage path

        Returns:
            Dict formatted for database insertion
        """
        # Extract data from Claude response
        data = claude_result.get("data", {})

        # Build match data dict
        match_data = {
            "id_jogo_cbf": id_jogo_cbf,
            "pdf_storage_path": storage_path,

            # Match details
            "data_jogo": data.get("data_jogo"),
            "hora_inicio": data.get("hora_inicio"),
            "competicao": data.get("competicao"),
            "fase": data.get("fase"),
            "rodada": data.get("rodada"),

            # Teams
            "time_mandante": data.get("time_mandante"),
            "time_visitante": data.get("time_visitante"),

            # Location
            "estadio": data.get("estadio"),
            "cidade": data.get("cidade"),
            "uf": data.get("uf"),

            # Score
            "placar_mandante": data.get("placar_mandante"),
            "placar_visitante": data.get("placar_visitante"),

            # Financial
            "receita_total": data.get("receita_total"),
            "despesa_total": data.get("despesa_total"),
            "saldo": data.get("saldo"),

            # Audience
            "publico_total": data.get("publico_total"),
            "publico_pagante": data.get("publico_pagante"),
            "publico_nao_pagante": data.get("publico_nao_pagante"),
            "renda_liquida": data.get("renda_liquida"),

            # Ticket pricing
            "preco_ingresso_min": data.get("preco_ingresso_min"),
            "preco_ingresso_max": data.get("preco_ingresso_max"),
            "preco_ingresso_medio": data.get("preco_ingresso_medio"),

            # Metadata
            "processado_em": datetime.now().isoformat(),
            "modelo_ia": "claude-haiku-4-5-20251001",
        }

        # Remove None values
        return {k: v for k, v in match_data.items() if v is not None}

    def _refresh_normalizations(self):
        """
        Refresh name normalization lookups using Claude.
        """
        try:
            logger.info("Refreshing normalization lookups...")

            # Get all matches
            matches = self.db.get_all_matches()

            # Extract unique names
            teams = set()
            stadiums = set()
            competitions = set()

            for match in matches:
                if match.get("time_mandante"):
                    teams.add(match["time_mandante"])
                if match.get("time_visitante"):
                    teams.add(match["time_visitante"])
                if match.get("estadio"):
                    stadiums.add(match["estadio"])
                if match.get("competicao"):
                    competitions.add(match["competicao"])

            # Normalize each category
            for category, names in [
                ("team", teams),
                ("stadium", stadiums),
                ("competition", competitions)
            ]:
                if not names:
                    continue

                logger.info(f"Normalizing {len(names)} {category} names...")

                # Get existing lookup
                existing = self.db.get_normalization_lookup(category)

                # Normalize with Claude
                new_mappings = self.claude.normalize_names(
                    names=list(names),
                    category=category,
                    existing_mappings=existing
                )

                # Update database
                if new_mappings:
                    self.db.update_normalization_lookup(category, new_mappings)
                    logger.info(f"Updated {len(new_mappings)} {category} normalizations")

            # Update normalized names in match records
            self._apply_normalizations()

            logger.info("Normalization refresh complete")

        except Exception as e:
            logger.error(f"Error refreshing normalizations: {e}")

    def _apply_normalizations(self):
        """
        Apply normalization lookups to all match records.
        """
        try:
            # Get lookups
            team_lookup = self.db.get_normalization_lookup("team")
            stadium_lookup = self.db.get_normalization_lookup("stadium")

            # Get all matches
            matches = self.db.get_all_matches()

            # Update each match
            for match in matches:
                id_jogo = match["id_jogo_cbf"]
                updates = {}

                # Normalize team names
                mandante = match.get("time_mandante")
                if mandante and mandante in team_lookup:
                    updates["time_mandante_normalizado"] = team_lookup[mandante]

                visitante = match.get("time_visitante")
                if visitante and visitante in team_lookup:
                    updates["time_visitante_normalizado"] = team_lookup[visitante]

                # Normalize stadium name
                estadio = match.get("estadio")
                if estadio and estadio in stadium_lookup:
                    updates["estadio_normalizado"] = stadium_lookup[estadio]

                # Apply updates
                if updates:
                    self.db.update_match(id_jogo, updates)

            logger.info(f"Applied normalizations to {len(matches)} matches")

        except Exception as e:
            logger.error(f"Error applying normalizations: {e}")

    def health_check(self) -> bool:
        """
        Health check endpoint for Railway/Render.

        Returns:
            True if all systems operational
        """
        try:
            # Check database connection
            self.db.get_all_matches(limit=1)

            # Check storage connection
            self.storage.list_pdfs()

            logger.info("Health check passed")
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# ============================================================================
# Entry Points
# ============================================================================

def run_scheduled_job():
    """
    Entry point for scheduled job (Railway cron, Render cron job, etc.)

    Set environment variable RUN_ONCE=true for single execution.
    """
    try:
        worker = CloudWorker()
        stats = worker.scrape_and_process()

        # Exit with status code based on errors
        if stats["errors"] > 0:
            logger.warning(f"Job completed with {stats['errors']} errors")
            sys.exit(1)
        else:
            logger.info("Job completed successfully")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error in scheduled job: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_continuous():
    """
    Entry point for continuous execution with schedule library.
    """
    import schedule
    import time

    logger.info("Starting continuous worker with schedule")

    # Schedule job to run daily at 2 AM
    schedule.every().day.at("02:00").do(run_scheduled_job)

    # Also run immediately on startup
    run_scheduled_job()

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    # Check if running in "run once" mode
    run_once = os.getenv("RUN_ONCE", "").lower() in ("true", "1", "yes")

    if run_once:
        logger.info("Running in RUN_ONCE mode")
        run_scheduled_job()
    else:
        logger.info("Running in continuous mode")
        run_continuous()
