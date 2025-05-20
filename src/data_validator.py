import pandas as pd
from pathlib import Path
import logging
from typing import List, Dict, Any
from datetime import datetime  # Added for date validation

# Configure a dedicated logger for data validation alerts
def setup_validation_logger(log_file_path: Path) -> logging.Logger:
    logger = logging.getLogger('DataValidator')
    logger.setLevel(logging.INFO)
    # Prevent duplicate handlers if this function is called multiple times
    if not logger.handlers:
        handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def validate_data_integrity(jogos_resumo_csv_path: Path, alerts_log_path: Path) -> int:
    """
    Scans jogos_resumo.csv for data anomalies and logs alerts.

    Args:
        jogos_resumo_csv_path (Path): Path to the jogos_resumo.csv file.
        alerts_log_path (Path): Path to save the validation alerts log.

    Returns:
        int: The number of alerts found.
    """
    validator_logger = setup_validation_logger(alerts_log_path)
    alerts_found = 0

    if not jogos_resumo_csv_path.exists():
        validator_logger.error(f"CSV file not found: {jogos_resumo_csv_path}")
        return 0

    try:
        df = pd.read_csv(jogos_resumo_csv_path, dtype={'id_jogo_cbf': str})
    except Exception as e:
        validator_logger.error(f"Error reading CSV file {jogos_resumo_csv_path}: {e}")
        return 0

    numeric_cols = ['receita_bruta_total', 'resultado_liquido', 
                    'publico_total', 'publico_pagante', 'publico_nao_pagante']
    for col in numeric_cols:
        if (col in df.columns):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            validator_logger.warning(f"Column '{col}' not found in {jogos_resumo_csv_path}. Skipping its validation.")


    for index, row in df.iterrows():
        game_id = str(row.get('id_jogo_cbf', f"ROW_{index}"))

        # Check for future game dates
        if 'data_jogo' in df.columns and pd.notna(row['data_jogo']):
            try:
                # Explicitly parse as day/month/year (Brazilian format)
                game_date = pd.to_datetime(row['data_jogo'], format='%d/%m/%Y', errors='coerce')
                if pd.notna(game_date) and game_date.date() > datetime.today().date():
                    alerts_found += 1
                    validator_logger.warning(f"ALERT: id_jogo_cbf='{game_id}', issue='Game date in the future', data_jogo='{row['data_jogo']}'")
            except Exception as e:
                validator_logger.warning(f"Could not parse date for id_jogo_cbf='{game_id}': {row['data_jogo']} (error: {e})")

        # Check negative revenue
        if 'receita_bruta_total' in df.columns and pd.notna(row['receita_bruta_total']) and row['receita_bruta_total'] < 0:
            alerts_found += 1
            validator_logger.warning(f"ALERT: id_jogo_cbf='{game_id}', issue='Negative revenue', column='receita_bruta_total', value={row['receita_bruta_total']}")

        # Check negative attendance
        for col_name in ['publico_total', 'publico_pagante', 'publico_nao_pagante']:
            if col_name in df.columns and pd.notna(row[col_name]) and row[col_name] < 0:
                alerts_found += 1
                validator_logger.warning(f"ALERT: id_jogo_cbf='{game_id}', issue='Negative attendance', column='{col_name}', value={row[col_name]}")

        # Check margin over 100%
        if 'receita_bruta_total' in df.columns and 'resultado_liquido' in df.columns:
            receita = row['receita_bruta_total']
            resultado = row['resultado_liquido']
            if pd.notna(receita) and pd.notna(resultado):
                if receita > 0:
                    margin = resultado / receita
                    if margin > 1.0:
                        alerts_found += 1
                        validator_logger.warning(f"ALERT: id_jogo_cbf='{game_id}', issue='Margin > 100%', receita_bruta_total={receita}, resultado_liquido={resultado}, calculated_margin={margin:.2%}")
                elif receita == 0 and resultado != 0:
                    alerts_found +=1
                    validator_logger.warning(f"ALERT: id_jogo_cbf='{game_id}', issue='Non-zero result with zero revenue', receita_bruta_total={receita}, resultado_liquido={resultado}")
                # Negative revenue already handled, margin calculation is ill-defined or less critical than the negative revenue itself.
    
    if alerts_found == 0:
        validator_logger.info("Data validation scan complete. No alerts found.")
    else:
        validator_logger.info(f"Data validation scan complete. {alerts_found} alerts found. See details above.")
        
    return alerts_found

if __name__ == '__main__':
    # Example usage (for testing purposes)
    project_root = Path(__file__).parent.parent 
    test_csv_path = project_root / 'csv' / 'jogos_resumo.csv'
    test_alerts_log_path = project_root / 'data_validation_alerts.log'
    
    # Create a dummy CSV for testing if it doesn't exist
    if not test_csv_path.exists():
        test_csv_path.parent.mkdir(parents=True, exist_ok=True)
        dummy_data = {
            'id_jogo_cbf': ['101', '102', '103', '104', '105', '106', '107'],
            'receita_bruta_total': [100000, -5000, 200000, 0, 50000, 10000, 0],
            'resultado_liquido': [50000, 1000, 250000, 1000, -60000, 1000, 0],
            'publico_total': [10000, 15000, -200, 5000, 8000, 0, 0],
            'publico_pagante': [8000, 12000, 100, -300, 7000, 0, 0],
            'publico_nao_pagante': [2000, 3000, -300, 5300, 1000, 0, 0]
        }
        pd.DataFrame(dummy_data).to_csv(test_csv_path, index=False)
        print(f"Created dummy CSV for testing: {test_csv_path}")

    print(f"Running validation on: {test_csv_path}")
    print(f"Alerts will be logged to: {test_alerts_log_path}")
    num_alerts = validate_data_integrity(test_csv_path, test_alerts_log_path)
    print(f"Validation complete. Number of alerts: {num_alerts}")
