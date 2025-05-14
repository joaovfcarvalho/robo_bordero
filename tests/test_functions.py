import pytest
from src.db import append_to_csv, read_csv
from src.scraper import download_pdfs
from src.gemini import analyze_pdf_with_gemini
import os # Added for file operations in tests

# Fixture for a temporary test CSV file
@pytest.fixture
def temp_csv_file(tmp_path):
    return tmp_path / "test.csv"

# Fixture for a dummy PDF file path
@pytest.fixture
def dummy_pdf_path(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_text("dummy PDF content") # Create a dummy file
    return str(pdf_path)

# Fixture for a dummy download directory
@pytest.fixture
def dummy_download_dir(tmp_path):
    return str(tmp_path / "test_pdfs")

def test_append_to_csv(temp_csv_file):
    # Test appending to a CSV file
    data = [{"id": 1, "name": "Test"}]
    headers = ["id", "name"]
    append_to_csv(str(temp_csv_file), data, headers)
    result = read_csv(str(temp_csv_file))
    assert result == data

    # Test appending more data
    data2 = [{"id": 2, "name": "Test2"}]
    append_to_csv(str(temp_csv_file), data2, headers)
    result2 = read_csv(str(temp_csv_file))
    assert result2 == data + data2


def test_read_csv(temp_csv_file):
    # Test reading from a CSV file
    # First, create a CSV file to read
    data = [{"id": 1, "name": "Test"}]
    headers = ["id", "name"]
    append_to_csv(str(temp_csv_file), data, headers)

    result = read_csv(str(temp_csv_file))
    assert isinstance(result, list)
    assert result == data

def test_read_empty_csv(temp_csv_file):
    # Test reading an empty or non-existent CSV, should return empty list
    # Ensure file does not exist or is empty
    if os.path.exists(temp_csv_file):
        os.remove(temp_csv_file)
    # Create an empty file for the read_csv function to find
    open(temp_csv_file, 'a').close()
    result = read_csv(str(temp_csv_file))
    assert result == []


def test_download_pdfs(mocker, dummy_download_dir):
    # Test downloading PDFs (mocked)
    # Mock requests.get to avoid actual downloads
    mocker.patch('src.scraper.requests.get')
    year = 2025
    competition_code = "142"
    # Use the fixture for download_dir
    result = download_pdfs(year, competition_code, dummy_download_dir, max_workers=1) # Added max_workers for testing
    assert isinstance(result, list)
    # Add more specific assertions if possible, e.g., based on expected file names if mock is set up to return specific content


def test_analyze_pdf_with_gemini(mocker, dummy_pdf_path):
    # Test analyzing a PDF (mocked)
    # Mock the GenerativeModel
    mock_model = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.text = '{"data": "analyzed_data"}' # Simulate Gemini response
    mock_model.generate_content.return_value = mock_response
    mocker.patch('src.gemini.genai.GenerativeModel', return_value=mock_model)
    
    api_key = "test_key" # This key won't actually be used due to mocking
    # Use the fixture for pdf_path
    result = analyze_pdf_with_gemini(api_key, dummy_pdf_path)
    assert isinstance(result, dict)
    assert result == {"data": "analyzed_data"}