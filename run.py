#!/usr/bin/env python3
"""
CBF Robot - Launcher script
This script starts the CBF Robot application.
"""
import os
import sys
# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import from the src folder directly
from src.main import main

# Debug: command-line entry for normalization
if len(sys.argv) == 2 and sys.argv[1].lower() == 'normalize':
    from src.main import run_normalization
    from dotenv import load_dotenv
    load_dotenv()
    from pathlib import Path
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    csv_dir = os.getenv("CSV_DIR", "csv")
    jogos_resumo_csv = Path(csv_dir) / "jogos_resumo.csv"
    clean_csv = Path(csv_dir) / "jogos_resumo_clean.csv"
    print("DEBUG: Running normalization via CLI")
    run_normalization(jogos_resumo_csv, Path("lookups"), clean_csv, gemini_api_key)
    sys.exit(0)

if __name__ == "__main__":
    main()