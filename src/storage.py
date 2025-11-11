"""
Supabase Storage module for CBF Robot.
Handles PDF uploads and file management in Supabase Storage buckets.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, BinaryIO
import structlog
from supabase import create_client, Client
from datetime import datetime

logger = structlog.get_logger(__name__)

# Bucket names
BUCKET_PDF = "pdfs"
BUCKET_CACHE = "cache"


class SupabaseStorage:
    """
    Manages file storage in Supabase Storage.

    Buckets:
    - pdfs: Match borderô PDFs (organized by year/id_jogo.pdf)
    - cache: Temporary cache files (JSON lookups, processing state)
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        """
        Initialize Supabase Storage client.

        Args:
            supabase_url: Supabase project URL (or from SUPABASE_URL env var)
            supabase_key: Supabase service role key (or from SUPABASE_SERVICE_KEY env var)
        """
        # Get credentials
        url = supabase_url or os.getenv("SUPABASE_URL")
        # Use service_role key for storage operations (has full access)
        key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError(
                "Supabase credentials not found. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
            )

        # Initialize client
        self.client: Client = create_client(url, key)
        self.storage = self.client.storage

        logger.info("Supabase Storage client initialized", url=url[:30] + "...")

    def _ensure_bucket_exists(self, bucket_name: str) -> bool:
        """
        Ensure a storage bucket exists, create if it doesn't.

        Args:
            bucket_name: Name of the bucket

        Returns:
            True if bucket exists or was created
        """
        try:
            # Try to get bucket
            buckets = self.storage.list_buckets()
            bucket_names = [b.name for b in buckets]

            if bucket_name in bucket_names:
                logger.debug(f"Bucket '{bucket_name}' already exists")
                return True

            # Create bucket if it doesn't exist
            self.storage.create_bucket(bucket_name, options={"public": False})
            logger.info(f"Created bucket '{bucket_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure bucket '{bucket_name}' exists: {e}")
            return False

    def upload_pdf(
        self,
        pdf_path: Path,
        year: int,
        id_jogo_cbf: str,
        overwrite: bool = False
    ) -> Optional[str]:
        """
        Upload a PDF borderô to Supabase Storage.

        Args:
            pdf_path: Local path to PDF file
            year: Year of the match (for folder organization)
            id_jogo_cbf: CBF match ID (e.g., "142-2025-001234")
            overwrite: If True, overwrite existing file

        Returns:
            Storage path (e.g., "2025/142-2025-001234.pdf") or None if failed
        """
        try:
            # Ensure bucket exists
            self._ensure_bucket_exists(BUCKET_PDF)

            # Build storage path: year/id_jogo.pdf
            storage_path = f"{year}/{id_jogo_cbf}.pdf"

            # Check if file already exists
            if not overwrite:
                try:
                    existing = self.storage.from_(BUCKET_PDF).list(path=str(year))
                    existing_files = [f["name"] for f in existing]
                    if f"{id_jogo_cbf}.pdf" in existing_files:
                        logger.debug(
                            f"PDF already exists in storage: {storage_path}",
                            id_jogo=id_jogo_cbf
                        )
                        return storage_path
                except Exception:
                    # If list fails, file probably doesn't exist, proceed with upload
                    pass

            # Read PDF file
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            # Upload to Supabase Storage
            result = self.storage.from_(BUCKET_PDF).upload(
                path=storage_path,
                file=pdf_data,
                file_options={
                    "content-type": "application/pdf",
                    "upsert": overwrite
                }
            )

            logger.info(
                f"Uploaded PDF to storage: {storage_path}",
                id_jogo=id_jogo_cbf,
                size_mb=round(len(pdf_data) / 1024 / 1024, 2)
            )

            return storage_path

        except Exception as e:
            logger.error(
                f"Failed to upload PDF: {e}",
                id_jogo=id_jogo_cbf,
                pdf_path=str(pdf_path)
            )
            return None

    def download_pdf(
        self,
        storage_path: str,
        local_path: Optional[Path] = None
    ) -> Optional[bytes]:
        """
        Download a PDF from Supabase Storage.

        Args:
            storage_path: Storage path (e.g., "2025/142-2025-001234.pdf")
            local_path: If provided, save to this local path

        Returns:
            PDF bytes or None if failed
        """
        try:
            # Download from storage
            response = self.storage.from_(BUCKET_PDF).download(storage_path)

            # Save to local file if requested
            if local_path:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(response)
                logger.info(f"Downloaded PDF to {local_path}")

            return response

        except Exception as e:
            logger.error(f"Failed to download PDF: {e}", storage_path=storage_path)
            return None

    def get_pdf_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a signed URL for accessing a PDF.

        Args:
            storage_path: Storage path (e.g., "2025/142-2025-001234.pdf")
            expires_in: URL expiration time in seconds (default: 1 hour)

        Returns:
            Signed URL or None if failed
        """
        try:
            result = self.storage.from_(BUCKET_PDF).create_signed_url(
                storage_path,
                expires_in
            )

            url = result.get("signedURL")
            logger.debug(f"Generated signed URL for {storage_path}")
            return url

        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}", storage_path=storage_path)
            return None

    def delete_pdf(self, storage_path: str) -> bool:
        """
        Delete a PDF from storage.

        Args:
            storage_path: Storage path (e.g., "2025/142-2025-001234.pdf")

        Returns:
            True if deleted successfully
        """
        try:
            self.storage.from_(BUCKET_PDF).remove([storage_path])
            logger.info(f"Deleted PDF from storage: {storage_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete PDF: {e}", storage_path=storage_path)
            return False

    def list_pdfs(self, year: Optional[int] = None) -> List[Dict]:
        """
        List all PDFs in storage.

        Args:
            year: If provided, only list PDFs from this year

        Returns:
            List of file metadata dicts
        """
        try:
            path = str(year) if year else ""
            files = self.storage.from_(BUCKET_PDF).list(path=path)

            logger.debug(f"Listed {len(files)} PDFs", year=year or "all")
            return files

        except Exception as e:
            logger.error(f"Failed to list PDFs: {e}", year=year)
            return []

    def upload_cache(
        self,
        data: bytes,
        cache_key: str,
        content_type: str = "application/json"
    ) -> bool:
        """
        Upload data to cache bucket.

        Args:
            data: Data to upload
            cache_key: Cache key (filename)
            content_type: MIME type

        Returns:
            True if uploaded successfully
        """
        try:
            # Ensure bucket exists
            self._ensure_bucket_exists(BUCKET_CACHE)

            # Upload
            self.storage.from_(BUCKET_CACHE).upload(
                path=cache_key,
                file=data,
                file_options={
                    "content-type": content_type,
                    "upsert": True
                }
            )

            logger.debug(f"Uploaded to cache: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload cache: {e}", cache_key=cache_key)
            return False

    def download_cache(self, cache_key: str) -> Optional[bytes]:
        """
        Download data from cache bucket.

        Args:
            cache_key: Cache key (filename)

        Returns:
            Cached data or None if not found
        """
        try:
            data = self.storage.from_(BUCKET_CACHE).download(cache_key)
            logger.debug(f"Downloaded from cache: {cache_key}")
            return data

        except Exception as e:
            logger.debug(f"Cache miss: {cache_key}")
            return None

    def get_storage_stats(self) -> Dict:
        """
        Get storage statistics.

        Returns:
            Dict with storage stats
        """
        try:
            pdf_files = self.list_pdfs()

            stats = {
                "total_pdfs": len(pdf_files),
                "total_size_mb": sum(f.get("metadata", {}).get("size", 0) for f in pdf_files) / 1024 / 1024,
                "buckets": [BUCKET_PDF, BUCKET_CACHE]
            }

            logger.info("Storage stats", **stats)
            return stats

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}


# Convenience function for getting a storage client
_storage_client: Optional[SupabaseStorage] = None


def get_storage_client() -> SupabaseStorage:
    """
    Get or create the global SupabaseStorage instance.

    Returns:
        Singleton SupabaseStorage client
    """
    global _storage_client
    if _storage_client is None:
        _storage_client = SupabaseStorage()
    return _storage_client
