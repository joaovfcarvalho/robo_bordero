import os
import requests
import concurrent.futures # Added
from .utils import (
    generate_urls,
    ensure_directory_exists,
    get_logger,
    handle_error,
    DownloadError,
    OperationCancelledError
)
from typing import Callable, Optional, List # List Added
import threading

def _download_single_pdf(url: str, year: int, competition_code: str, download_dir: str, logger) -> Optional[str]:
    """Downloads a single PDF file."""
    try:
        base_name = os.path.basename(url)
        name_part, ext = os.path.splitext(base_name)
        file_name = f"{name_part}_{year}{ext}"
        file_path = os.path.join(download_dir, file_name)

        if not os.path.exists(file_path):
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            with open(file_path, 'wb') as file:
                file.write(response.content)
            logger.info("Downloaded file",
                       filename=file_name,
                       url=url,
                       size_bytes=len(response.content))
            return file_path
        else:
            logger.debug("File already exists", filename=file_name, path=file_path)
            return file_path # Return path if already exists, considered a "success" for download purposes
    except requests.RequestException as e:
        error_context = {
            "url": url,
            "file_name": file_name if 'file_name' in locals() else base_name, # Ensure file_name is defined
            "year": year,
            "competition_code": competition_code
        }
        handle_error(
            error=DownloadError(f"Failed to download {url}: {str(e)}", error_context),
            log_context=error_context,
            log_level="warning"
        )
        return None
    except Exception as e: # Catch any other unexpected error during single download
        error_context = {
            "url": url,
            "file_name": file_name if 'file_name' in locals() else base_name,
            "year": year,
            "competition_code": competition_code
        }
        handle_error(
            error=DownloadError(f"Unexpected error downloading {url}: {str(e)}", error_context),
            log_context=error_context,
            log_level="error" # Log as error for unexpected issues
        )
        return None

def download_pdfs(year: int, competition_code: str, download_dir: str,
                  progress_callback: Optional[Callable[[float], None]] = None,
                  cancel_event: Optional[threading.Event] = None,
                  max_workers: int = 5) -> List[str]: # Added max_workers
    """
    Faz o download de PDFs de borderôs com base no ano e no código da competição,
    utilizando processamento paralelo.

    Args:
        year (int): Ano dos jogos.
        competition_code (str): Código da competição (142, 424, 242).
        download_dir (str): Diretório onde os PDFs serão salvos.
        progress_callback (Optional[Callable[[float], None]]): Callback to report progress (0.0 to 100.0).
        cancel_event (Optional[threading.Event]): Event to signal cancellation.
        max_workers (int): Número máximo de threads para download paralelo.

    Returns:
        list: Lista de arquivos baixados com sucesso (ou já existentes).
        
    Raises:
        OperationCancelledError: If the operation is cancelled.
    """
    logger = get_logger("downloader")
    ensure_directory_exists(download_dir)

    try:
        urls = generate_urls(year, competition_code)
    except Exception as e:
        handle_error(
            error=e,
            log_context={"year": year, "competition_code": competition_code},
            log_level="error"
        )
        return []

    downloaded_files: List[str] = []
    total_urls = len(urls)

    if total_urls == 0:
        if progress_callback:
            progress_callback(100.0)
        return []

    logger.info("Starting PDF downloads",
               year=year,
               competition=competition_code,
               url_count=total_urls,
               download_dir=str(download_dir),
               max_workers=max_workers)

    completed_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(_download_single_pdf, url, year, competition_code, download_dir, logger): url for url in urls}

        for future in concurrent.futures.as_completed(future_to_url):
            if cancel_event and cancel_event.is_set():
                logger.info("Download operation cancelled by user.")
                # Attempt to cancel remaining futures
                for f in future_to_url: # Iterate over keys of the dict
                    if not f.done():
                        f.cancel()
                executor.shutdown(wait=False, cancel_futures=True) # Python 3.9+ for cancel_futures
                raise OperationCancelledError("Download cancelled by user.")

            result_path = future.result()
            if result_path:
                downloaded_files.append(result_path)
            
            completed_count += 1
            if progress_callback:
                progress_percentage = (completed_count / total_urls) * 100
                progress_callback(progress_percentage)

    logger.info("Download completed",
               total_downloaded_or_existing=len(downloaded_files),
               total_attempted=total_urls)
    return downloaded_files