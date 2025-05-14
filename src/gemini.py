import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re
from io import BytesIO
import pdfplumber
import time

from .utils import (
    get_logger,
    handle_error,
    APIError,
    ConfigurationError
)

# Set up logger for this module
logger = get_logger("gemini")

# Define Pydantic models for structured output
class RevenueDetail(BaseModel):
    source: str
    quantity: int | None = None # Add quantity (optional integer)
    price: float | None = None # Add price (optional float)
    amount: float

class ExpenseDetail(BaseModel):
    category: str
    amount: float

class MatchDetails(BaseModel):
    home_team: str
    away_team: str
    match_date: str
    stadium: str
    competition: str

class FinancialData(BaseModel):
    gross_revenue: float
    total_expenses: float
    net_result: float
    revenue_details: List[RevenueDetail]
    expense_details: List[ExpenseDetail]

class AudienceStatistics(BaseModel):
    paid_attendance: int
    non_paid_attendance: int
    total_attendance: int

class PDFExtract(BaseModel):
    match_details: MatchDetails
    financial_data: FinancialData
    audience_statistics: AudienceStatistics

def setup_client():
    """
    Sets up the Google Gen AI using the API key from environment variables.

    Returns:
        genai.Client: Configured Gen AI client.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ConfigurationError("GEMINI_API_KEY environment variable is not set.")

    return genai.Client(api_key=api_key)

# Simple rule-based fallback parser using pdfplumber

def fallback_extract(pdf_content_bytes: bytes) -> dict:
    text = ""
    with pdfplumber.open(BytesIO(pdf_content_bytes)) as pdf:
        for page in pdf.pages:
            if page_text := page.extract_text():
                text += page_text + "\n"
    # Helper to parse monetary values
    def parse_amount(pattern):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1)
            try:
                return float(val.replace(".", "").replace(",", "."))
            except:
                return None
        return None
    gross_rev = parse_amount(r"Receita\s*Bruta(?:\s*Total)?:?\s*[R\$]*\s*([\d\.,]+)")
    total_exp = parse_amount(r"Despesa\s*Total:?")
    total_exp = parse_amount(r"Despesa\s*Total:?[R\$]*\s*([\d\.,]+)") if total_exp is None else total_exp
    net_res = None
    if gross_rev is not None and total_exp is not None:
        net_res = gross_rev - total_exp
    financial_data = {
        "gross_revenue": gross_rev,
        "total_expenses": total_exp,
        "net_result": net_res,
        "revenue_details": [],
        "expense_details": []
    }
    return {"financial_data": financial_data}

def analyze_pdf(pdf_content_bytes: bytes, custom_prompt: str = None) -> Dict[str, Any]:
    """
    Analyzes PDF content using the Google Gen AI API with a specified prompt.

    Args:
        pdf_content_bytes (bytes): The content of the PDF file as bytes.
        custom_prompt (str, optional): Custom prompt to guide the analysis. Defaults to a standard prompt.

    Returns:
        dict: Parsed JSON response from the Google Gen AI API or an error dictionary.
    """
    fallback_enabled = os.getenv("ENABLE_FALLBACK", "true").lower() in ("1","true","yes")
    retry_count = int(os.getenv("GEMINI_RETRY_COUNT", "3"))
    backoff = float(os.getenv("GEMINI_BACKOFF_SECONDS", "1"))

    try:
        client = setup_client()

        if not pdf_content_bytes:
            logger.error("Empty PDF content received")
            return {"error": "PDF content bytes are empty."}

        # Define the prompt
        default_prompt = (
            "Extract the following information from the PDF as a JSON object: "
            "1. Match details: home_team (str), away_team (str), match_date (str, YYYY-MM-DD), stadium (str), competition (str). "
            "2. Financial data: gross_revenue (float), total_expenses (float), net_result (float), revenue_details (list of dicts with 'source', 'quantity' (int), 'price' (float), and 'amount' (float) keys), expense_details (list of dicts with 'category' and 'amount' keys). "
            "3. Audience statistics: paid_attendance (int), non_paid_attendance (int), total_attendance (int)."
            "Ensure all monetary values are floats and attendances/quantities are integers. If a value (like quantity or price) is not applicable or found, use null."
        )
        prompt = custom_prompt if custom_prompt else default_prompt

        # Create the PDF part for document processing
        pdf_part = types.Part.from_bytes(data=pdf_content_bytes, mime_type="application/pdf")
        pdf_size_kb = len(pdf_content_bytes) / 1024

        # Log the API call
        logger.info("Sending PDF to Gemini API", 
                   pdf_size_kb=f"{pdf_size_kb:.2f}KB",
                   model="gemini-2.0-flash")

        # Retry API call on failure
        response = None
        for attempt in range(1, retry_count + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=[pdf_part, prompt],
                    config={
                        "temperature": 0.2,
                        "response_mime_type": "application/json",
                        "response_schema": PDFExtract
                    }
                )
                break
            except Exception as api_err:
                logger.warning("Gemini API call failed, retrying if attempts remain", attempt=attempt, error=str(api_err))
                if attempt < retry_count:
                    time.sleep(backoff * attempt)
                else:
                    raise

        # Return structured parsed output or fallback to raw JSON parse
        if response and response.parsed:
            logger.info("Successfully received structured response from API")
            return response.parsed.model_dump()
        elif response and response.text:
            logger.info("Received unstructured response, attempting JSON parse")
            try:
                return json.loads(response.text)
            except json.JSONDecodeError as json_err:
                error_details = {
                    "raw_response": response.text[:500] + ("..." if len(response.text) > 500 else ""),
                    "error_type": "JSONDecodeError"
                }
                error = APIError(f"Failed to parse JSON response: {json_err}", error_details)
                handle_error(error, error_details)
                return {"error": str(error), "raw_response_preview": error_details["raw_response"]}
        else:
            # Handle blocked or empty response
            block_reason = getattr(response.prompt_feedback, "block_reason", "Unknown") if hasattr(response, "prompt_feedback") else "Unknown"
            error_details = {"block_reason": block_reason}
            error = APIError(f"API response empty or blocked. Reason: {block_reason}", error_details)
            handle_error(error, error_details, log_level="warning")
            # Fallback on blocked/empty response
            if fallback_enabled:
                logger.info("Using fallback parser due to API block/empty response")
                return fallback_extract(pdf_content_bytes)
            return {"error": str(error)}

    except ConfigurationError as e:
        # Re-raise configuration errors for handling in the caller
        raise e
    except Exception as e:
        # Handle any other unexpected errors
        error_details = {"pdf_size_kb": f"{len(pdf_content_bytes) / 1024:.2f}KB" if pdf_content_bytes else "N/A"}
        error = APIError(f"Unexpected error in Gemini API call: {e}", error_details)
        handle_error(error, error_details)
        # Fallback on unexpected errors
        if fallback_enabled and pdf_content_bytes:
            logger.info("Fallback extractor triggered after unexpected error")
            return fallback_extract(pdf_content_bytes)
        return {"error": str(error)}