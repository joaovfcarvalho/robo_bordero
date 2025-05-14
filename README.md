# CBF Robot

## Overview
The CBF Robot is a Python-based application designed to automate the collection and intelligent analysis of match reports (borderôs) from the Brazilian Football Confederation (CBF) website. It utilizes web scraping techniques to gather data, integrates with the Google Gemini API for analysis, and stores structured data in CSV files. The application provides a simple Graphical User Interface (GUI) for interaction.

## Features
- **Web Scraping**: Automatically downloads PDF match reports (borderôs) from the CBF website for specified competitions and years.
- **AI-Powered Data Extraction**: Uses the Google Gemini API to analyze the content of the PDF reports, extracting key information like match details, financial data, and audience statistics.
- **CSV Storage**: Stores the extracted data in structured CSV files (`jogos_resumo.csv`, `receitas_detalhe.csv`, `despesas_detalhe.csv`) for easy access and analysis.
- **GUI Interface**: Offers a simple Tkinter-based GUI to choose operations (download, analyze, or both).
- **Logging**: Records operations and errors to `cbf_robot.log`.

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
│   └── __pycache__/      # Python cache files (auto-generated)
├── tests/
│   └── test_functions.py # Placeholder for unit tests
├── .env                  # Environment variables (user-created)
├── requirements.txt      # Project dependencies
├── README.md             # This file
└── cbf_robot.log         # Log file (auto-generated)
```

## Setup Instructions
1.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd cbf-robot
    ```

2.  **Install Dependencies**:
    Ensure you have Python 3.7 or higher installed. Then, install the required packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**:
    Create a `.env` file in the root directory (`cbf-robot/`) and add the necessary environment variables. Example:
    ```env
    # Year to fetch borderôs for
    YEAR=2025
    # Competition codes (e.g., 142=Série A, 424=Copa do Brasil, 242=Série B)
    COMPETITIONS=142,424,242
    # Directory to save downloaded PDFs
    PDF_DIR=pdfs
    # Directory to save output CSVs
    CSV_DIR=csv
    # Your Google AI Studio API Key for Gemini
    GEMINI_API_KEY=your_google_gemini_api_key_here
    ```
    *   You can obtain a `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/).

4.  **Run the Application**:
    Execute the main script from the root directory using Python:
    ```bash
    python src/main.py
    ```
    This will open the application's GUI window.

## Usage

When you run the application (`python src/main.py`), a small window will appear with three buttons:

1.  **1. Apenas download de novos borderôs**: Clicks this to download PDF borderôs for the year and competitions specified in your `.env` file. It will only download files that are not already present in the `PDF_DIR`.
2.  **2. Apenas análise de borderôs não processados**: Click this to analyze the PDFs currently in the `PDF_DIR` using the Gemini API. It checks the `jogos_resumo.csv` file and only processes PDFs whose IDs are not already listed, saving the results to the CSV files in `CSV_DIR`.
3.  **3. Download e análise (execução completa)**: Click this to perform both steps sequentially: first download new PDFs, then analyze any unprocessed PDFs.

A message box will appear indicating when the selected operation is complete.

## Output Files

-   **`pdfs/`**: Contains the downloaded PDF borderô files.
-   **`csv/jogos_resumo.csv`**: Contains summary information for each processed match.
-   **`csv/receitas_detalhe.csv`**: Contains detailed revenue information for each processed match.
-   **`csv/despesas_detalhe.csv`**: Contains detailed expense information for each processed match.
-   **`cbf_robot.log`**: Contains logs of operations, including downloads, analysis attempts, successes, and errors.

## Security Note
Your `GEMINI_API_KEY` is sensitive. Ensure the `.env` file is included in your `.gitignore` file to prevent accidentally committing it to version control.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. (You may want to add a LICENSE file).

## Future Improvements

*   **Optimize PDF Downloading:** Currently, the script generates URLs for all possible match IDs for a given competition and year, even if many don't exist or have already been downloaded. A future optimization could involve:
    *   Checking the `pdfs/` directory more efficiently before attempting downloads (though it already skips existing files).
    *   Potentially finding a way to query an API or source that lists only *valid* match report URLs for a given competition/year, rather than iterating through all possibilities.
    *   Alternatively, tracking the last successfully downloaded ID per competition/year and starting the scan from there on subsequent runs.

## Next Steps
- Develop an interactive dashboard (e.g., using Dash, Streamlit, or Power BI) that reads the following cleaned output files:
  - `csv/jogos_resumo_clean.csv`
  - `csv/receitas_detalhe.csv`
  - `csv/despesas_detalhe.csv`
- Include visual metrics and filters such as:
  - Total matches, revenues, and expenses by competition, team, or stadium
  - Time-series plots of attendance and revenue over the season
  - Breakdown of revenue sources and expense categories
  - Comparison between home and away team performance
- Provide deployment instructions for hosting the dashboard locally or in the cloud (Heroku/Azure/GCP).