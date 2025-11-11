"""
Supabase Database module for CBF Robot.
Handles PostgreSQL database operations via Supabase client.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import structlog
from supabase import create_client, Client
from decimal import Decimal

logger = structlog.get_logger(__name__)


class SupabaseDatabase:
    """
    Manages database operations in Supabase PostgreSQL.

    Tables:
    - jogos_resumo: Match summary information
    - receitas_detalhe: Detailed revenue breakdown
    - despesas_detalhe: Detailed expense breakdown
    - processing_queue: PDF processing queue
    - normalization_lookups: Name normalization mappings
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        """
        Initialize Supabase Database client.

        Args:
            supabase_url: Supabase project URL (or from SUPABASE_URL env var)
            supabase_key: Supabase service role key (or from SUPABASE_SERVICE_KEY env var)
        """
        # Get credentials
        url = supabase_url or os.getenv("SUPABASE_URL")
        # Prefer service_role key for backend operations, fall back to anon key
        key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError(
                "Supabase credentials not found. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
            )

        # Initialize client
        self.client: Client = create_client(url, key)

        logger.info("Supabase Database client initialized", url=url[:30] + "...")

    # ========================================================================
    # Match Operations (jogos_resumo)
    # ========================================================================

    def match_exists(self, id_jogo_cbf: str) -> bool:
        """
        Check if a match already exists in the database.

        Args:
            id_jogo_cbf: CBF match ID

        Returns:
            True if match exists
        """
        try:
            result = self.client.table("jogos_resumo") \
                .select("id_jogo_cbf") \
                .eq("id_jogo_cbf", id_jogo_cbf) \
                .execute()

            exists = len(result.data) > 0
            logger.debug(f"Match exists check: {id_jogo_cbf}", exists=exists)
            return exists

        except Exception as e:
            logger.error(f"Failed to check if match exists: {e}", id_jogo=id_jogo_cbf)
            return False

    def add_match(self, match_data: Dict[str, Any]) -> bool:
        """
        Add a new match to the database.

        Args:
            match_data: Dict containing match information

        Returns:
            True if successful
        """
        try:
            # Insert match
            result = self.client.table("jogos_resumo").insert(match_data).execute()

            logger.info(
                "Added match to database",
                id_jogo=match_data.get("id_jogo_cbf"),
                mandante=match_data.get("time_mandante"),
                visitante=match_data.get("time_visitante")
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to add match: {e}",
                id_jogo=match_data.get("id_jogo_cbf")
            )
            return False

    def update_match(self, id_jogo_cbf: str, match_data: Dict[str, Any]) -> bool:
        """
        Update an existing match.

        Args:
            id_jogo_cbf: CBF match ID
            match_data: Dict containing fields to update

        Returns:
            True if successful
        """
        try:
            result = self.client.table("jogos_resumo") \
                .update(match_data) \
                .eq("id_jogo_cbf", id_jogo_cbf) \
                .execute()

            logger.info(f"Updated match: {id_jogo_cbf}")
            return True

        except Exception as e:
            logger.error(f"Failed to update match: {e}", id_jogo=id_jogo_cbf)
            return False

    def get_match(self, id_jogo_cbf: str) -> Optional[Dict]:
        """
        Get a match by ID.

        Args:
            id_jogo_cbf: CBF match ID

        Returns:
            Match data dict or None
        """
        try:
            result = self.client.table("jogos_resumo") \
                .select("*") \
                .eq("id_jogo_cbf", id_jogo_cbf) \
                .execute()

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get match: {e}", id_jogo=id_jogo_cbf)
            return None

    def get_all_matches(
        self,
        year: Optional[int] = None,
        team: Optional[str] = None,
        competition: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get all matches with optional filters.

        Args:
            year: Filter by year
            team: Filter by team (mandante or visitante)
            competition: Filter by competition
            limit: Maximum number of results

        Returns:
            List of match dicts
        """
        try:
            query = self.client.table("jogos_resumo").select("*")

            # Apply filters
            if year:
                query = query.gte("data_jogo", f"{year}-01-01") \
                             .lte("data_jogo", f"{year}-12-31")

            if team:
                # Search in both mandante and visitante (normalized names)
                query = query.or_(
                    f"time_mandante_normalizado.eq.{team},"
                    f"time_visitante_normalizado.eq.{team}"
                )

            if competition:
                query = query.eq("competicao", competition)

            # Execute with limit
            result = query.limit(limit).order("data_jogo", desc=True).execute()

            logger.debug(f"Retrieved {len(result.data)} matches", year=year, team=team)
            return result.data

        except Exception as e:
            logger.error(f"Failed to get matches: {e}")
            return []

    def delete_match(self, id_jogo_cbf: str) -> bool:
        """
        Delete a match and its related data (cascading).

        Args:
            id_jogo_cbf: CBF match ID

        Returns:
            True if successful
        """
        try:
            result = self.client.table("jogos_resumo") \
                .delete() \
                .eq("id_jogo_cbf", id_jogo_cbf) \
                .execute()

            logger.info(f"Deleted match: {id_jogo_cbf}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete match: {e}", id_jogo=id_jogo_cbf)
            return False

    # ========================================================================
    # Revenue/Expense Details
    # ========================================================================

    def add_revenue_details(
        self,
        id_jogo_cbf: str,
        revenues: List[Dict[str, Any]]
    ) -> bool:
        """
        Add revenue details for a match.

        Args:
            id_jogo_cbf: CBF match ID
            revenues: List of revenue dicts with 'categoria' and 'valor'

        Returns:
            True if successful
        """
        try:
            # Add id_jogo_cbf to each revenue item
            items = [{"id_jogo_cbf": id_jogo_cbf, **rev} for rev in revenues]

            result = self.client.table("receitas_detalhe").insert(items).execute()

            logger.info(f"Added {len(revenues)} revenue items", id_jogo=id_jogo_cbf)
            return True

        except Exception as e:
            logger.error(f"Failed to add revenue details: {e}", id_jogo=id_jogo_cbf)
            return False

    def add_expense_details(
        self,
        id_jogo_cbf: str,
        expenses: List[Dict[str, Any]]
    ) -> bool:
        """
        Add expense details for a match.

        Args:
            id_jogo_cbf: CBF match ID
            expenses: List of expense dicts with 'categoria' and 'valor'

        Returns:
            True if successful
        """
        try:
            # Add id_jogo_cbf to each expense item
            items = [{"id_jogo_cbf": id_jogo_cbf, **exp} for exp in expenses]

            result = self.client.table("despesas_detalhe").insert(items).execute()

            logger.info(f"Added {len(expenses)} expense items", id_jogo=id_jogo_cbf)
            return True

        except Exception as e:
            logger.error(f"Failed to add expense details: {e}", id_jogo=id_jogo_cbf)
            return False

    def get_revenue_details(self, id_jogo_cbf: str) -> List[Dict]:
        """
        Get revenue details for a match.

        Args:
            id_jogo_cbf: CBF match ID

        Returns:
            List of revenue dicts
        """
        try:
            result = self.client.table("receitas_detalhe") \
                .select("*") \
                .eq("id_jogo_cbf", id_jogo_cbf) \
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get revenue details: {e}", id_jogo=id_jogo_cbf)
            return []

    def get_expense_details(self, id_jogo_cbf: str) -> List[Dict]:
        """
        Get expense details for a match.

        Args:
            id_jogo_cbf: CBF match ID

        Returns:
            List of expense dicts
        """
        try:
            result = self.client.table("despesas_detalhe") \
                .select("*") \
                .eq("id_jogo_cbf", id_jogo_cbf) \
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get expense details: {e}", id_jogo=id_jogo_cbf)
            return []

    # ========================================================================
    # Processing Queue
    # ========================================================================

    def add_to_queue(
        self,
        id_jogo_cbf: str,
        pdf_url: str,
        competicao: str,
        ano: int
    ) -> bool:
        """
        Add a match to the processing queue.

        Args:
            id_jogo_cbf: CBF match ID
            pdf_url: URL to download PDF
            competicao: Competition name
            ano: Year

        Returns:
            True if successful
        """
        try:
            data = {
                "id_jogo_cbf": id_jogo_cbf,
                "pdf_url": pdf_url,
                "competicao": competicao,
                "ano": ano,
                "status": "pending"
            }

            result = self.client.table("processing_queue").insert(data).execute()

            logger.info(f"Added to processing queue: {id_jogo_cbf}")
            return True

        except Exception as e:
            logger.error(f"Failed to add to queue: {e}", id_jogo=id_jogo_cbf)
            return False

    def get_pending_queue_items(self, limit: int = 10) -> List[Dict]:
        """
        Get pending items from processing queue.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of queue item dicts
        """
        try:
            result = self.client.table("processing_queue") \
                .select("*") \
                .eq("status", "pending") \
                .order("adicionado_em") \
                .limit(limit) \
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get pending queue items: {e}")
            return []

    def update_queue_status(
        self,
        id_jogo_cbf: str,
        status: str,
        error: Optional[str] = None
    ) -> bool:
        """
        Update queue item status.

        Args:
            id_jogo_cbf: CBF match ID
            status: New status ('processing', 'completed', 'failed')
            error: Error message if failed

        Returns:
            True if successful
        """
        try:
            data = {"status": status}

            if status == "completed":
                data["processado_em"] = datetime.now().isoformat()

            if error:
                data["ultimo_erro"] = error

            result = self.client.table("processing_queue") \
                .update(data) \
                .eq("id_jogo_cbf", id_jogo_cbf) \
                .execute()

            logger.info(f"Updated queue status: {id_jogo_cbf}", status=status)
            return True

        except Exception as e:
            logger.error(f"Failed to update queue status: {e}", id_jogo=id_jogo_cbf)
            return False

    # ========================================================================
    # Name Normalization
    # ========================================================================

    def get_normalization_lookup(self, category: str) -> Dict[str, str]:
        """
        Get normalization lookup for a category.

        Args:
            category: 'team', 'stadium', or 'competition'

        Returns:
            Dict mapping original names to normalized names
        """
        try:
            result = self.client.table("normalization_lookups") \
                .select("nome_original", "nome_normalizado") \
                .eq("categoria", category) \
                .execute()

            lookup = {
                row["nome_original"]: row["nome_normalizado"]
                for row in result.data
            }

            logger.debug(f"Retrieved {len(lookup)} {category} normalizations")
            return lookup

        except Exception as e:
            logger.error(f"Failed to get normalization lookup: {e}", category=category)
            return {}

    def update_normalization_lookup(
        self,
        category: str,
        mappings: Dict[str, str]
    ) -> bool:
        """
        Update normalization lookup with new mappings.

        Args:
            category: 'team', 'stadium', or 'competition'
            mappings: Dict of original -> normalized names

        Returns:
            True if successful
        """
        try:
            # Build upsert data
            data = [
                {
                    "categoria": category,
                    "nome_original": original,
                    "nome_normalizado": normalized
                }
                for original, normalized in mappings.items()
            ]

            # Upsert (insert or update)
            result = self.client.table("normalization_lookups") \
                .upsert(data) \
                .execute()

            logger.info(f"Updated {len(mappings)} {category} normalizations")
            return True

        except Exception as e:
            logger.error(f"Failed to update normalization lookup: {e}", category=category)
            return False

    # ========================================================================
    # Statistics & Analytics
    # ========================================================================

    def get_team_stats(self, team: str) -> Dict[str, Any]:
        """
        Get statistics for a team.

        Args:
            team: Team name (normalized)

        Returns:
            Dict with team statistics
        """
        try:
            # Get all matches for this team as mandante
            result = self.client.table("jogos_resumo") \
                .select("*") \
                .eq("time_mandante_normalizado", team) \
                .execute()

            matches = result.data

            if not matches:
                return {}

            # Calculate stats
            stats = {
                "total_jogos": len(matches),
                "receita_total": sum(m.get("receita_total", 0) or 0 for m in matches),
                "receita_media": sum(m.get("receita_total", 0) or 0 for m in matches) / len(matches) if matches else 0,
                "publico_total": sum(m.get("publico_total", 0) or 0 for m in matches),
                "publico_medio": sum(m.get("publico_total", 0) or 0 for m in matches) / len(matches) if matches else 0,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get team stats: {e}", team=team)
            return {}

    def execute_custom_query(self, query: str) -> List[Dict]:
        """
        Execute a custom SQL query (for NLQ dashboard).

        Args:
            query: SQL query string

        Returns:
            Query results as list of dicts
        """
        try:
            # Use rpc for custom SQL
            result = self.client.rpc("custom_query", {"query": query}).execute()
            return result.data

        except Exception as e:
            logger.error(f"Failed to execute custom query: {e}")
            return []


# Convenience function for getting a database client
_db_client: Optional[SupabaseDatabase] = None


def get_database_client() -> SupabaseDatabase:
    """
    Get or create the global SupabaseDatabase instance.

    Returns:
        Singleton SupabaseDatabase client
    """
    global _db_client
    if _db_client is None:
        _db_client = SupabaseDatabase()
    return _db_client
