import os
import csv
from .utils import (
    get_logger,
    handle_error,
    DataValidationError
)

# Set up logger for this module
logger = get_logger("database")

def append_to_csv(file_path, data, headers):
    """
    Adiciona dados a um arquivo CSV, criando o arquivo com cabeçalho se ele não existir.

    Args:
        file_path (str): Caminho do arquivo CSV.
        data (list): Lista de dicionários contendo os dados a serem adicionados.
        headers (list): Lista de cabeçalhos do CSV.
    """
    log_context = {
        "file_path": str(file_path),
        "row_count": len(data) if data else 0
    }

    try:
        # Validate inputs
        if not data:
            logger.warning("No data to append", **log_context)
            return

        if not headers:
            error = DataValidationError("Headers list cannot be empty", log_context)
            handle_error(error, log_context)
            return

        # Check if file exists
        file_exists = os.path.exists(file_path)
        log_context["file_exists"] = file_exists

        # Process data to ensure all required headers are present
        processed_data = []
        for row in data:
            processed_row = {header: row.get(header) for header in headers}
            processed_data.append(processed_row)

        # Write to CSV
        with open(file_path, mode='a', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers, extrasaction='ignore')

            if not file_exists or os.path.getsize(file_path) == 0:
                writer.writeheader()
                logger.info("Created new CSV file with headers", **log_context)
            else:
                logger.debug("Appending to existing CSV", **log_context)

            writer.writerows(processed_data)
            logger.info("Successfully wrote data to CSV", **log_context)

    except IOError as e:
        error = DataValidationError(f"I/O error writing to CSV file: {str(e)}", log_context)
        handle_error(error, log_context)
    except csv.Error as e:
        error = DataValidationError(f"CSV formatting error: {str(e)}", log_context)
        handle_error(error, log_context)
    except Exception as e:
        handle_error(e, log_context)

def read_csv(file_path):
    """
    Lê o conteúdo de um arquivo CSV e retorna como uma lista de dicionários.

    Args:
        file_path (str): Caminho do arquivo CSV.

    Returns:
        list: Lista de dicionários representando as linhas do CSV.
    """
    log_context = {"file_path": str(file_path)}

    try:
        if not os.path.exists(file_path):
            logger.warning("CSV file not found, returning empty list", **log_context)
            return []

        with open(file_path, mode='r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            
            # Handle potential empty file or file with only headers
            data = list(reader)
            log_context["row_count"] = len(data)
            
            if not data and reader.fieldnames is None:
                logger.warning("CSV file is empty or has no headers", **log_context)
                return []
                
            logger.info("Successfully read CSV data", **log_context)
            return data
            
    except FileNotFoundError:
        logger.warning("CSV file not found during read operation", **log_context)
        return []
    except IOError as e:
        error = DataValidationError(f"I/O error reading CSV file: {str(e)}", log_context)
        handle_error(error, log_context, log_level="error")
        return []
    except csv.Error as e:
        error = DataValidationError(f"CSV parsing error: {str(e)}", log_context)
        handle_error(error, log_context, log_level="error")
        return []
    except Exception as e:
        handle_error(e, log_context, log_level="critical")
        return []