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
from src.main import main, run_normalization
from pathlib import Path
import json

# Debug: command-line entry for normalization
if len(sys.argv) == 2 and sys.argv[1].lower() == 'normalize':
    config = {}
    config_file = Path("config.json")
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except Exception:
            pass # Handle error or use defaults

    gemini_api_key = config.get("gemini_api_key")
    csv_dir = config.get("csv_dir", "csv")

    if not gemini_api_key:
        print("ERROR: GEMINI_API_KEY not found in config.json. Please run the main application to configure it.")
        sys.exit(1)

    jogos_resumo_csv = Path(csv_dir) / "jogos_resumo.csv"
    clean_csv = Path(csv_dir) / "jogos_resumo_clean.csv"
    print("DEBUG: Running normalization via CLI")
    run_normalization(jogos_resumo_csv, Path("lookups"), clean_csv, gemini_api_key)
    sys.exit(0)

if __name__ == "__main__":
    main()