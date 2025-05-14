import os
from dotenv import load_dotenv
import logging
import logging.handlers
import structlog
import sys
import traceback
from typing import Optional, Dict, Any, Callable, Union

# Exception Hierarchy for CBF Robot
class CBFRobotError(Exception):
    """Base exception class for all CBF Robot errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

class DownloadError(CBFRobotError):
    """Exception raised for errors during PDF download."""
    pass

class ProcessingError(CBFRobotError):
    """Exception raised for errors during PDF processing."""
    pass

class APIError(CBFRobotError):
    """Exception raised for errors related to external API calls."""
    pass

class DataValidationError(CBFRobotError):
    """Exception raised for data validation errors."""
    pass

class ConfigurationError(CBFRobotError):
    """Exception raised for configuration errors."""
    pass

class OperationCancelledError(CBFRobotError):
    """Exception raised when an operation is cancelled by the user."""
    pass

# Structured logging processor for additional context
def add_app_context(_, __, event_dict):
    """Add application context to log records."""
    event_dict["app"] = "CBF Robot"
    return event_dict

def load_env_variables():
    """Load environment variables from the .env file."""
    load_dotenv()

def setup_logging():
    """
    Configures rotating logging for the application using structlog.
    Logs daily, keeping the last 7 days.
    """
    log_file = 'cbf_robot.log'
    log_level = logging.INFO
    
    # Create a handler that rotates daily and keeps 7 backups
    handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='D',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_app_context,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure formatter for the handler
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
    )
    
    handler.setFormatter(formatter)
    
    # Get the root logger and add the handler
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers first to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    root_logger.addHandler(handler)
    
    # Also log to console for interactive use
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Return a structlog logger instance
    return structlog.get_logger()

# Helper function to create a logger
def get_logger(name: str = None):
    """
    Get a structured logger instance.
    
    Args:
        name: Optional module name for the logger
        
    Returns:
        A structlog logger instance
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()

def handle_error(
    error: Exception, 
    log_context: Optional[Dict[str, Any]] = None,
    ui_callback: Optional[Callable[[str, str], None]] = None,
    raise_exception: bool = False,
    log_level: str = "error"
) -> Dict[str, Any]:
    """
    Centralized error handling function.
    
    Args:
        error: The exception that was raised
        log_context: Additional context to include in the log
        ui_callback: Optional callback function for UI feedback (e.g., messagebox.showerror)
        raise_exception: Whether to re-raise the exception after handling
        log_level: Log level to use ("error", "warning", "critical", etc.)
        
    Returns:
        Dict containing error details
    """
    logger = get_logger()
    context = log_context or {}
    
    # Extract error details
    error_type = type(error).__name__
    error_message = str(error)
    error_traceback = traceback.format_exc()
    
    # Prepare error details
    error_details = {
        "error_type": error_type,
        "error_message": error_message,
        "traceback": error_traceback,
        **context
    }
    
    # Log the error with appropriate level
    log_method = getattr(logger, log_level)
    log_method("Error occurred", **error_details)
    
    # UI feedback if callback is provided
    if ui_callback and callable(ui_callback):
        ui_callback("Erro", f"{error_type}: {error_message}")
    
    # Re-raise if requested
    if raise_exception:
        raise error
        
    return error_details

def generate_urls(year, competition_code):
    """
    Gera URLs para download de borderôs com base no ano e no código da competição,
    considerando as regras de numeração específicas.

    Args:
        year (int): Ano dos jogos.
        competition_code (str): Código da competição (142, 424, 242).

    Returns:
        list: Lista de URLs geradas.
    """
    urls = []
    base_url = f"https://conteudo.cbf.com.br/sumulas/{year}/"

    if competition_code == "142": # Série A - Rounds 1-38, Matches 0-9
        for round_number in range(1, 39): # Rounds 1 to 38
            for match_in_round in range(10): # Matches 0 to 9
                match_id = f"{competition_code}{round_number}{match_in_round}"
                url = f"{base_url}{match_id}b.pdf"
                urls.append(url)

    elif competition_code == "424": # Copa do Brasil - Sequential 1 to 150
        for match_number in range(1, 151): # Matches 1 to 150
            match_id = f"{competition_code}{match_number}"
            url = f"{base_url}{match_id}b.pdf"
            urls.append(url)

    elif competition_code == "242": # Série B - Sequential 1 to 380
        for match_number in range(1, 381): # Matches 1 to 380
            match_id = f"{competition_code}{match_number}"
            url = f"{base_url}{match_id}b.pdf"
            urls.append(url)

    else:
        logger = get_logger()
        logger.warning("Unknown competition code", competition_code=competition_code)
        raise ConfigurationError(f"Código de competição desconhecido ou não suportado: {competition_code}")

    return urls

def ensure_directory_exists(directory):
    """
    Garante que o diretório especificado existe, criando-o se necessário.

    Args:
        directory (str): Caminho do diretório.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)