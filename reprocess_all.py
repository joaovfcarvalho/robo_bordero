from src.main import reprocess_all_pdfs
import json

# Load API key from config.json
def get_api_key():
    try:
        with open("config.json") as f:
            config = json.load(f)
        return config.get("gemini_api_key")
    except Exception:
        print("Could not load Gemini API key from config.json.")
        return None

def main():
    api_key = get_api_key()
    if not api_key:
        print("No Gemini API key found. Exiting.")
        return
    reprocess_all_pdfs(
        pdf_dir="pdfs",
        jogos_resumo_csv="csv/jogos_resumo.csv",
        receitas_detalhe_csv=None,  # Not used anymore
        despesas_detalhe_csv=None,  # Not used anymore
        gemini_api_key=api_key
    )

if __name__ == "__main__":
    main()
