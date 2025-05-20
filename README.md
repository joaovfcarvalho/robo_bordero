# CBF Robot

## Overview
The CBF Robot is a Python-based application designed to automate the collection and intelligent analysis of match reports (borderôs) from the Brazilian Football Confederation (CBF) website. It utilizes web scraping techniques to gather data, integrates with the Google Gemini API for analysis, and stores structured data in CSV files. The application provides a simple Graphical User Interface (GUI) for interaction.

## Features
- **Web Scraping:** Automatically downloads PDF match reports (borderôs) from the CBF website for specified competitions and years.
- **AI-Powered Data Extraction:** Uses the Google Gemini API to analyze the content of the PDF reports, extracting key information like match details, financial data, and audience statistics.
- **CSV Storage:** Stores the extracted data in structured CSV files (`jogos_resumo.csv`, `receitas_detalhe.csv`, `despesas_detalhe.csv`) for easy access and analysis.
- **GUI Interface:** Offers a Tkinter-based GUI to choose operations (download, analyze, or both) and manage settings.
- **Configuration Management:** Saves settings like API keys, directories, and competition lists in a `config.json` file.
- **Logging:** Records operations and errors to `cbf_robot.log`.
- **Data Validation:** Validates extracted data and logs alerts for anomalies.
- **Dashboard:** Provides a Streamlit dashboard for data visualization.

## Project Structure
```
cbf-robot/
├── csv/                  # Directory for output CSV files
├── pdfs/                 # Directory for downloaded PDF borderôs
├── src/
│   ├── main.py           # Main application script with GUI
│   ├── scraper.py        # Functions for downloading PDFs
│   ├── gemini.py         # Functions for interacting with Google Gemini API
│   ├── db.py             # Functions for reading/writing CSV files
│   ├── utils.py          # Utility functions (URL generation, logging setup)
│   ├── normalize.py      # Name normalization logic
│   ├── validation.py     # Data validation logic
│   ├── data_validator.py # Data integrity checks
│   ├── dashboard.py      # Streamlit dashboard
│   └── __pycache__/      # Python cache files (auto-generated)
├── tests/                # Unit and integration tests
├── config.json           # Configuration file (user-managed or auto-generated)
├── requirements.txt      # Project dependencies
├── README.md             # This file
└── cbf_robot.log         # Log file (auto-generated)
```

## Setup Instructions
1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd cbf-robot
    ```

2.  **Install Dependencies:**
    Ensure you have Python 3.7 or higher installed. Then, install the required packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Key and Settings:**
    When you first run the application, or if the `config.json` file is missing or does not contain the Gemini API Key, you will be prompted to enter it via the GUI.
    You can also manage settings (API Key, PDF/CSV directories, competitions) through the "Configurações" menu in the application. These settings are saved in `config.json` in the root directory.
    
    Example of `config.json`:
    ```json
    {
      "year": 2025,
      "competitions": [
        "142",
        "424",
        "242"
      ],
      "pdf_dir": "pdfs",
      "csv_dir": "csv",
      "gemini_api_key": "your_google_gemini_api_key_here"
    }
    ```
    *   You can obtain a `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/).

4.  **Run the Application:**
    Execute the main script from the root directory using Python:
    ```bash
    python src/main.py 
    ```
    or if you made `run.py` executable:
    ```bash
    python run.py
    ```
    This will open the application's GUI window.

## Usage

When you run the application, a small window will appear. Use the "Configurações" menu to set your API key and other preferences if you haven't already.

The main window has five buttons for operations:

1.  **1. Apenas download de novos borderôs:** Downloads PDF borderôs for the year and competitions specified in your settings. It only downloads files not already present.
2.  **2. Apenas análise de borderôs não processados:** Analyzes PDFs in the `PDF_DIR` using the Gemini API. It checks `jogos_resumo.csv` and processes only new PDFs.
3.  **3. Download e análise (execução completa):** Performs both download and analysis sequentially.
4.  **4. Normalizar Nomes (CSV):** Processes `jogos_resumo.csv` to create/update `jogos_resumo_clean.csv` by normalizing team, stadium, and competition names using lookups (which may also be refreshed using the Gemini API if new names are found).
5.  **5. Validar Dados (jogos_resumo.csv):** Runs data integrity checks and logs alerts for anomalies.

A message box will indicate when an operation is complete. Progress is shown in a bar at the bottom of the window.

## Output Files

-   **`pdfs/`**: Contains the downloaded PDF borderô files.
-   **`csv/jogos_resumo.csv`**: Summary information for each processed match.
-   **`csv/receitas_detalhe.csv`**: Detailed revenue information.
-   **`csv/despesas_detalhe.csv`**: Detailed expense information.
-   **`csv/jogos_resumo_clean.csv`**: Cleaned version of `jogos_resumo.csv` with normalized names.
-   **`lookups/`**: Contains JSON files used for normalizing names (e.g., `teams_lookup.json`).
-   **`cbf_robot.log`**: Logs of operations, successes, and errors.
-   **`config.json`**: Stores user settings.
-   **`data_validation_alerts.log`**: Logs of data validation alerts.

## Security Note
Your `GEMINI_API_KEY` is sensitive. The `config.json` file, where the API key is stored, should be added to your `.gitignore` file if you are in a shared repository and want to avoid committing your personal key. For personal use or if `config.json` contains only non-sensitive default settings, you might choose to keep it under version control.

**Planned improvement:** In a future version, the API key will be stored securely using the OS keyring and removed from plaintext in `config.json`.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. (You may want to add a LICENSE file).

## Future Improvements

*   **Optimize PDF Downloading:** 
    *   More efficient checking of existing files.
    *   Querying a source for valid match report URLs.
    *   Tracking last downloaded ID per competition/year.
*   **Database Backend:**
    *   Add SQLite support for scalable, reliable storage.
    *   Provide migration scripts from CSV to database.
*   **Validation Alerts in GUI:**
    *   Display data validation alerts directly in the GUI after processing.
*   **Log Viewer:**
    *   Add a log viewer to the GUI for error and validation logs.
*   **Extensibility:**
    *   Allow new competitions or formats to be added via configuration files, not code changes.

## Next Steps
- Develop an interactive dashboard (e.g., using Streamlit) that reads the following cleaned output files:
  - `csv/jogos_resumo_clean.csv`
  - `csv/receitas_detalhe.csv`
  - `csv/despesas_detalhe.csv`
- Include visual metrics and filters such as:
  - Total matches, revenues, and expenses by competition, team, or stadium
  - Time-series plots of attendance and revenue over the season
  - Breakdown of revenue sources and expense categories
  - Comparison between home and away team performance
- Provide deployment instructions for hosting the dashboard locally or in the cloud (Heroku/Azure/GCP).