# CBF Robot Implementation Plan (May 20, 2025)

## Overview

This plan details actionable steps to address the critical evaluation findings and recommendations for the CBF Robot application. Each step is designed to be clear and actionable for an AI agent or developer.

---

## 1. Download Efficiency

- Refactor `generate_urls` and `download_pdfs` to:
  - Accept a list of valid match IDs (from a scraped schedule or CBF API, if available).
  - If no API is available, implement a scraper to extract valid match IDs from the CBF website.
  - Only generate/download URLs for valid matches.

## 2. Test Coverage

- Add unit and integration tests for:
  - `normalize.py` (name normalization logic).
  - `validation.py` (data validation logic).
  - `data_validator.py` (integrity checks).
  - GUI logic (using `pytest-tkinter` or similar).
- Add test fixtures with sample PDFs and CSVs.
- Ensure all new features are covered by tests.

## 3. Documentation

- Add/expand docstrings for all public functions and classes.
- Add usage examples where appropriate.
- Update the README to:
  - Document new features (e.g., validation alerts in GUI, database backend).
  - Add a section on security and API key management.
  - Add a section on extensibility (how to add new competitions).

## 4. GUI Enhancements

- Add a log viewer to the GUI for error and validation logs.
- Display data validation alerts in the GUI after processing.
- Add advanced filtering and search for processed matches.

## 5. Database Backend

- Add SQLite (via SQLAlchemy) as an optional backend.
- Create models for matches, revenues, and expenses.
- Add migration scripts to import existing CSV data into the database.
- Update the application to optionally use the database for storage and queries.

## 6. Parallel PDF Analysis

- Refactor PDF analysis in `process_pdfs` to use `concurrent.futures.ThreadPoolExecutor` or `ProcessPoolExecutor`.
- Allow configuration of the number of parallel workers.
- Ensure thread/process safety for CSV/database writes.

## 7. Validation Alerts in GUI

- After processing, read the validation alerts log and display a summary in the GUI.
- Provide a button to view detailed alerts.

## 8. Secure API Key Storage

- Integrate with the OS keyring (e.g., `keyring` Python package) to store/retrieve the Gemini API key.
- Remove the API key from plaintext in `config.json`.
- Update documentation to reflect the new approach.

## 9. Extensibility

- Refactor competition and match format logic to be data-driven (e.g., via a JSON or YAML config).
- Allow new competitions or formats to be added without code changes.

---

## Implementation Notes

- Each step should include code, tests, and documentation updates.
- All new features must be covered by automated tests.
- Back up existing data before migrations.
- Ensure backward compatibility where possible.

---

**Created: May 20, 2025**