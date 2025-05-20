import os
import sys
import logging
import tkinter as tk
import datetime
from tkinter import messagebox, ttk, filedialog
from pathlib import Path
from .scraper import download_pdfs
from .gemini import analyze_pdf
from .db import append_to_csv, read_csv
from .utils import (
    setup_logging, 
    ensure_directory_exists,
    get_logger,
    handle_error,
    CBFRobotError,
    ProcessingError,
    ConfigurationError,
    OperationCancelledError # Added
)
from .normalize import refresh_lookups, write_clean_csv
import json
from .validation import validate_summary, validate_revenue, validate_expense
from .data_validator import validate_data_integrity # Added
import threading
from typing import Callable, Optional, List # Added

# Set up structured logging
logger = setup_logging()

def run_normalization(jogos_resumo_csv_path: Path, lookup_dir: Path, clean_csv_path: Path, gemini_api_key: str):
    """
    Runs the lookup refresh and clean CSV writing process.
    """
    try:
        logger.info("Starting normalization process")
        refresh_lookups(jogos_resumo_csv_path, lookup_dir, gemini_api_key)
        write_clean_csv(jogos_resumo_csv_path, clean_csv_path, lookup_dir)
        messagebox.showinfo("Sucesso", "Normalização de nomes concluída. Arquivo 'jogos_resumo_clean.csv' criado/atualizado.")
        logger.info("Normalization process finished successfully")
    except Exception as e:
        handle_error(
            error=e,
            log_context={"process": "normalization", "input_file": str(jogos_resumo_csv_path)},
            ui_callback=messagebox.showerror
        )

def run_operation(choice, year, competitions, pdf_dir, csv_dir, gemini_api_key,
                  progress_callback: Optional[Callable[[float], None]] = None,
                  cancel_event: Optional[threading.Event] = None):
    """
    Executes the selected operation based on the user's choice.
    """
    # Define paths using pathlib
    pdf_path = Path(pdf_dir)
    csv_path = Path(csv_dir)
    lookup_path = Path("lookups") 
    jogos_resumo_csv = csv_path / "jogos_resumo.csv"
    receitas_detalhe_csv = csv_path / "receitas_detalhe.csv"
    despesas_detalhe_csv = csv_path / "despesas_detalhe.csv"
    jogos_resumo_clean_csv = csv_path / "jogos_resumo_clean.csv" 

    failed_pdfs = []

    try:
        operation_context = {
            "operation": choice,
            "year": year,
            "competitions": competitions,
            "pdf_dir": str(pdf_path),
            "csv_dir": str(csv_path)
        }

        if choice == "1": # Download PDFs
            logger.info("Starting PDF download", **operation_context)
            num_competitions = len(competitions)
            if num_competitions == 0 and progress_callback:
                progress_callback(100.0)
                
            for competition_idx, competition in enumerate(competitions):
                if cancel_event and cancel_event.is_set():
                    raise OperationCancelledError("Download operation cancelled.")
                
                def sub_progress_download(p_comp): # p_comp is 0-100 for current competition
                    if progress_callback:
                        overall_p = (competition_idx / num_competitions) * 100 + (p_comp / num_competitions)
                        progress_callback(overall_p)
                
                download_pdfs(year, competition, pdf_path, progress_callback=sub_progress_download, cancel_event=cancel_event)
            
            if progress_callback and not (cancel_event and cancel_event.is_set()) and competitions: # Ensure 100% if completed
                progress_callback(100.0)

            if not (cancel_event and cancel_event.is_set()):
                messagebox.showinfo("Sucesso", "Download dos PDFs concluído.")
            logger.info("PDF download completed", **operation_context)

        elif choice == "2": # Process PDFs
            logger.info("Starting PDF processing", **operation_context)
            failed_pdfs = process_pdfs(pdf_path, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key, progress_callback=progress_callback, cancel_event=cancel_event)
            
            if not (cancel_event and cancel_event.is_set()):
                if failed_pdfs:
                    messagebox.showwarning("Processamento Concluído com Erros", f"Processamento dos PDFs concluído. Os seguintes PDFs não puderam ser processados: {', '.join(failed_pdfs)}")
                else:
                    messagebox.showinfo("Sucesso", "Processamento dos PDFs concluído.")
            logger.info("PDF processing completed", failed_count=len(failed_pdfs), **operation_context)

        elif choice == "3": # Download and Process
            logger.info("Starting download and processing", **operation_context)
            
            num_download_steps = len(competitions)
            total_steps = num_download_steps + 1 # N competitions for download + 1 for processing
            current_task_idx = 0 # Tracks completion of major tasks (each download, then processing)

            if total_steps == 1 and progress_callback: # Only processing, no competitions to download
                 pass # process_pdfs will handle its own 0-100%

            # Download part
            for i, competition in enumerate(competitions):
                if cancel_event and cancel_event.is_set():
                    raise OperationCancelledError("Download and Process operation cancelled during download phase.")
                
                def download_phase_sub_progress(percentage_of_current_download_task): # 0-100
                    if progress_callback:
                        # Progress within the current download task's allocated portion
                        progress_of_this_task_scaled = percentage_of_current_download_task / total_steps
                        progress_of_completed_tasks = current_task_idx / total_steps
                        overall_progress = (progress_of_completed_tasks + progress_of_this_task_scaled) * 100
                        progress_callback(overall_progress)

                download_pdfs(year, competition, pdf_path, progress_callback=download_phase_sub_progress, cancel_event=cancel_event)
                current_task_idx += 1
                # Ensure this step's progress is fully accounted for if download_phase_sub_progress didn't hit 100% for its segment
                if progress_callback and not (cancel_event and cancel_event.is_set()):
                    progress_callback((current_task_idx / total_steps) * 100)


            if cancel_event and cancel_event.is_set():
                raise OperationCancelledError("Download and Process operation cancelled before processing phase.")

            # Processing part
            def processing_phase_sub_progress(percentage_of_processing_task): # 0-100
                if progress_callback:
                    progress_of_this_task_scaled = percentage_of_processing_task / total_steps
                    progress_of_completed_tasks = current_task_idx / total_steps # current_task_idx is now num_download_steps
                    overall_progress = (progress_of_completed_tasks + progress_of_this_task_scaled) * 100
                    progress_callback(overall_progress)
            
            failed_pdfs = process_pdfs(pdf_path, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key, progress_callback=processing_phase_sub_progress, cancel_event=cancel_event)
            current_task_idx +=1 
            
            if progress_callback and not (cancel_event and cancel_event.is_set()): # Ensure 100% at the end
                progress_callback(100.0)

            if not (cancel_event and cancel_event.is_set()):
                if failed_pdfs:
                    messagebox.showwarning("Concluído com Erros", f"Download e processamento concluídos. Os seguintes PDFs não puderam ser processados: {', '.join(failed_pdfs)}")
                else:
                    messagebox.showinfo("Sucesso", "Download e processamento dos PDFs concluídos.")
            logger.info("Download and processing completed", failed_count=len(failed_pdfs), **operation_context)

        elif choice == "4": # Normalize CSV
            logger.info("Starting CSV normalization", **operation_context)
            # Normalization is typically fast, but we can set progress to 0 and 100
            if progress_callback: progress_callback(0)
            if cancel_event and cancel_event.is_set(): raise OperationCancelledError("Normalization cancelled.")
            run_normalization(jogos_resumo_csv, lookup_path, jogos_resumo_clean_csv, gemini_api_key)
            if progress_callback: progress_callback(100)
            # Message is shown within run_normalization

        elif choice == "5": # Validate Data Integrity
            logger.info("Starting data integrity validation", **operation_context)
            if progress_callback: progress_callback(0)
            if cancel_event and cancel_event.is_set(): raise OperationCancelledError("Data validation cancelled.")
            
            alerts_log_file = Path("data_validation_alerts.log") # Log in the root directory
            num_alerts = validate_data_integrity(jogos_resumo_csv, alerts_log_file)
            
            if progress_callback: progress_callback(100)
            
            if not (cancel_event and cancel_event.is_set()):
                if num_alerts > 0:
                    messagebox.showwarning("Validação Concluída", f"{num_alerts} alertas de integridade de dados encontrados. Verifique o arquivo '{alerts_log_file.name}' para detalhes.")
                else:
                    messagebox.showinfo("Validação Concluída", f"Nenhum alerta de integridade de dados encontrado. O arquivo '{alerts_log_file.name}' foi gerado.")
            logger.info("Data integrity validation completed", alert_count=num_alerts, log_file=str(alerts_log_file))

        else:
            error_message = f"Seleção inválida: {choice}"
            logger.warning(error_message, **operation_context)
            messagebox.showwarning("Seleção Inválida", "Por favor, selecione uma operação válida.")
    
    except OperationCancelledError as e:
        logger.info(f"Operation cancelled: {str(e)}", **operation_context)
        messagebox.showinfo("Operação Cancelada", str(e))
    except CBFRobotError as e:
        # Handle custom application exceptions
        handle_error(
            error=e,
            log_context={"operation_details": operation_context},
            ui_callback=messagebox.showerror
        )
    except Exception as e:
        # Handle unexpected exceptions
        handle_error(
            error=e,
            log_context={"operation_details": operation_context},
            ui_callback=messagebox.showerror,
            log_level="critical"
        )

def main():
    """
    Ponto de entrada principal para executar as operações de download e análise.
    Agora com interface gráfica.
    """

    # Initialize main window before creating control variables
    root = tk.Tk()
    root.title("CBF Robot")

    try:
        # Configurações - Get defaults, but year will be overridden by GUI
        # default_year = int(os.getenv("YEAR", datetime.date.today().year)) # Removed
        # competitions = os.getenv("COMPETITIONS", "142,424,242").split(",") # Removed
        # pdf_dir = os.getenv("PDF_DIR", "pdfs") # Removed
        # csv_dir = os.getenv("CSV_DIR", "csv") # Removed
        # gemini_api_key = os.getenv("GEMINI_API_KEY") # Removed

        # Use hardcoded defaults or load from config.json for these
        default_year = datetime.date.today().year
        competitions = ["142", "424", "242"] # Default competitions
        pdf_dir = "pdfs"
        csv_dir = "csv"
        gemini_api_key = "" # Will be loaded from config.json or prompted

        # Load persistent GUI settings if available
        config_file = Path("config.json")
        if config_file.exists():
            try:
                stored = json.loads(config_file.read_text())
                default_year = stored.get("year", default_year) # Load year from config
                competitions = stored.get("competitions", competitions)
                pdf_dir = stored.get("pdf_dir", pdf_dir)
                csv_dir = stored.get("csv_dir", csv_dir)
                gemini_api_key = stored.get("gemini_api_key", gemini_api_key)
            except Exception as e:
                logger.warning(f"Failed to load config.json: {e}") # Log error
                pass # Keep defaults if config loading fails

        # Settings storage and GUI variables
        settings = {"year": default_year, "competitions": competitions, "pdf_dir": pdf_dir, "csv_dir": csv_dir, "gemini_api_key": gemini_api_key}
        year_var = tk.StringVar(value=str(settings["year"])) # Use loaded/default year
        competitions_var = tk.StringVar(value=",".join(settings["competitions"]))
        pdf_dir_var = tk.StringVar(value=settings["pdf_dir"])
        csv_dir_var = tk.StringVar(value=settings["csv_dir"])
        api_key_var = tk.StringVar(value=settings["gemini_api_key"])

        def open_settings():
            settings_win = tk.Toplevel(root)
            settings_win.title("Configurações")
            tk.Label(settings_win, text="Chave API Gemini:").grid(row=0, column=0, sticky='e')
            tk.Entry(settings_win, textvariable=api_key_var, width=30).grid(row=0, column=1)
            tk.Label(settings_win, text="Diretório PDFs:").grid(row=1, column=0, sticky='e')
            tk.Entry(settings_win, textvariable=pdf_dir_var, width=30).grid(row=1, column=1)
            tk.Button(settings_win, text="Browse...", command=lambda: pdf_dir_var.set(filedialog.askdirectory())).grid(row=1, column=2)
            tk.Label(settings_win, text="Diretório CSVs:").grid(row=2, column=0, sticky='e')
            tk.Entry(settings_win, textvariable=csv_dir_var, width=30).grid(row=2, column=1)
            tk.Button(settings_win, text="Browse...", command=lambda: csv_dir_var.set(filedialog.askdirectory())).grid(row=2, column=2)
            tk.Label(settings_win, text="Competições (IDs separados por vírgula):").grid(row=3, column=0, sticky='e')
            tk.Entry(settings_win, textvariable=competitions_var, width=30).grid(row=3, column=1)
            def save_settings():
                settings["year"] = int(year_var.get()) # Save year
                settings["competitions"] = competitions_var.get().split(",")
                settings["pdf_dir"] = pdf_dir_var.get()
                settings["csv_dir"] = csv_dir_var.get()
                settings["gemini_api_key"] = api_key_var.get()
                # Persist settings
                try:
                    config_file.write_text(json.dumps(settings, indent=2))
                except Exception:
                    pass
                messagebox.showinfo("Configurações", "Configurações salvas com sucesso.")
                settings_win.destroy()
            tk.Button(settings_win, text="Salvar", command=save_settings).grid(row=4, column=0, pady=10)
            tk.Button(settings_win, text="Cancelar", command=settings_win.destroy).grid(row=4, column=1, pady=10)

        # Operation execution with UI state management
        operation_buttons = []
        cancel_event_ref = [None] # Using a list to pass by reference for modification in task
        current_thread_ref = [None] # Store current running thread

        def update_progress(percentage):
            progress_var.set(percentage)
            root.update_idletasks() # Ensure UI updates

        def prompt_for_api_key_if_needed():
            """Prompts the user for the API key if it's not already set."""
            if not settings.get("gemini_api_key"):
                # Use simpledialog to ask for the key
                # This needs to be run in the main thread, so we might need to adjust
                # how it's called or handle it before starting the thread if the key is missing.
                # For now, let's assume it can be called and will block appropriately.
                # The actual prompt should ideally happen before starting the thread or be managed carefully.
                # A better approach might be to check before even calling threaded_operation for these choices.
                # For this iteration, we'll try to prompt and if it fails, we exit the task.
                key = tk.simpledialog.askstring("Chave da API Gemini", 
                                                "Por favor, insira sua chave da API Gemini:", 
                                                parent=root)
                if key:
                    settings["gemini_api_key"] = key
                    api_key_var.set(key)
                    # Persist the new key
                    try:
                        config_file.write_text(json.dumps(settings, indent=2))
                    except Exception as e:
                        logger.error("Failed to save API key to config.json", error=str(e))
                    return True
                else:
                    messagebox.showwarning("Chave da API Necessária", 
                                           "A chave da API Gemini é necessária para esta operação.")
                    return False
            return True # Key already exists

        def threaded_operation(choice):
            # If another operation is running, do nothing or show a message
            if current_thread_ref[0] and current_thread_ref[0].is_alive():
                messagebox.showwarning("Operação em Andamento", "Outra operação já está em execução. Por favor, aguarde ou cancele.")
                return

            cancel_event = threading.Event()
            cancel_event_ref[0] = cancel_event
            
            def task():
                # Check for API key if needed by the operation
                if choice in ["2", "3", "4"]: # Operations requiring API key
                    if not settings.get("gemini_api_key"):
                        # Prompt for API key in a way that doesn't block the UI thread improperly
                        # This is tricky. For now, let's call a function that handles this.
                        # The actual prompt should ideally happen before the thread starts or be managed carefully.
                        # A better approach might be to check before even calling threaded_operation for these choices.
                        # For this iteration, we'll try to prompt and if it fails, we exit the task.
                        
                        # We need to run the dialog in the main thread. 
                        # A simple way is to schedule it and wait, but that's complex from a worker thread.
                        # The prompt_for_api_key_if_needed was designed to be called from main thread.
                        # Let's adjust: check key, if missing, show error and don't start.
                        # This check should ideally be outside the thread, before starting it.
                        # Re-evaluating: The prompt should be before this task() starts.
                        pass # API key check will be done before starting the thread for relevant operations

                for btn in operation_buttons:
                    btn.config(state='disabled')
                cancel_button.config(state='normal') # Enable cancel button
                status_var.set(f"Operação {choice} iniciada...")
                progress_var.set(0) # Reset progress
                progress_bar.config(mode='determinate')


                try:
                    run_operation(choice, int(year_var.get()), settings["competitions"], 
                                  settings["pdf_dir"], settings["csv_dir"], settings["gemini_api_key"],
                                  progress_callback=update_progress, cancel_event=cancel_event)
                    # Status message is now handled by run_operation or its sub-functions for success/failure/cancellation
                    # So, we might not need a generic success message here unless no specific message was shown.
                    if not cancel_event.is_set(): # Only set to generic "completed" if not cancelled
                        # Check if a specific message was already shown by run_operation
                        # This is tricky, perhaps run_operation should return a status message string
                        # For now, let's assume run_operation's message boxes are sufficient.
                        # status_var.set(f"Operação {choice} concluída.") # Or specific message from run_operation
                        pass # Messages are handled within run_operation

                except Exception as e: # Catch any other unexpected error from run_operation itself
                    status_var.set(f"Erro inesperado na operação {choice}: {str(e)}")
                    handle_error(e, log_context={"operation": choice}, ui_callback=messagebox.showerror)
                finally:
                    progress_bar.config(mode='determinate') # Keep determinate
                    if not cancel_event.is_set(): # If not cancelled, ensure progress is 100%
                         progress_var.set(100)
                    else: # If cancelled, reflect that it didn't complete to 100% unless it did before cancelling
                         pass # Progress var should be at its last updated state or reset if desired
                    
                    status_var.set("Pronto") # Reset status or show final status from operation
                    for btn in operation_buttons:
                        btn.config(state='normal')
                    cancel_button.config(state='disabled') # Disable cancel button
                    cancel_event_ref[0] = None
                    current_thread_ref[0] = None

            thread = threading.Thread(target=task, daemon=True)
            current_thread_ref[0] = thread
            thread.start()

        # Menu bar with Settings
        menubar = tk.Menu(root)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Configurações", command=open_settings)
        menubar.add_cascade(label="Configurações", menu=settings_menu)
        root.config(menu=menubar)

        # Year selection
        tk.Label(root, text="Ano para Download:").pack(pady=(10, 0))
        year_var = tk.StringVar(value=str(default_year))
        year_entry = tk.Entry(root, textvariable=year_var, width=10)
        year_entry.pack(pady=(0, 10))

        tk.Label(root, text="Selecione a operação:").pack(pady=10)

        # Status bar
        status_var = tk.StringVar(value="Pronto")
        status_label = tk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor='w')
        status_label.pack(side=tk.BOTTOM, fill='x')

        # Progress bar
        progress_var = tk.DoubleVar() # Variable for progress bar
        progress_bar = ttk.Progressbar(root, mode='determinate', variable=progress_var, maximum=100) # Changed mode
        progress_bar.pack(side=tk.BOTTOM, fill='x')

        # Operation buttons
        btn1 = tk.Button(root, text="1. Apenas download de novos borderôs", command=lambda: threaded_operation("1"))
        btn1.pack(pady=5)
        
        def operation_requires_api_key(op_choice):
            return op_choice in ["2", "3", "4"]

        def create_operation_lambda(op_choice):
            def op_lambda():
                if operation_requires_api_key(op_choice):
                    if not prompt_for_api_key_if_needed():
                        return # Don't proceed if API key is not provided
                threaded_operation(op_choice)
            return op_lambda

        btn2 = tk.Button(root, text="2. Apenas análise de borderôs não processados", command=create_operation_lambda("2"))
        btn2.pack(pady=5)
        btn3 = tk.Button(root, text="3. Download e análise (execução completa)", command=create_operation_lambda("3"))
        btn3.pack(pady=5)
        btn4 = tk.Button(root, text="4. Normalizar Nomes (CSV)", command=create_operation_lambda("4"))
        btn4.pack(pady=5)

        btn5 = tk.Button(root, text="5. Validar Dados (jogos_resumo.csv)", command=create_operation_lambda("5"))
        btn5.pack(pady=5)
        operation_buttons.extend([btn1, btn2, btn3, btn4, btn5])

        # Cancel button
        def on_cancel():
            if cancel_event_ref[0]:
                cancel_event_ref[0].set()
                status_var.set("Cancelando operação...")
        
        cancel_button = tk.Button(root, text="Cancelar Operação", command=on_cancel, state='disabled')
        cancel_button.pack(pady=5)


        root.mainloop()
        
    except ConfigurationError as e:
        # Handle configuration errors specially since UI might not be available yet
        handle_error(
            error=e,
            log_level="critical",
            ui_callback=lambda title, msg: messagebox.showerror(title, msg) if 'root' in locals() else print(f"{title}: {msg}")
        )
        sys.exit(1)
    except Exception as e:
        # Handle any other initialization errors
        handle_error(
            error=e,
            log_level="critical",
            ui_callback=lambda title, msg: messagebox.showerror(title, msg) if 'root' in locals() else print(f"{title}: {msg}")
        )
        sys.exit(1)

def process_pdfs(pdf_dir: Path, jogos_resumo_csv: Path, 
                 receitas_detalhe_csv: Path, despesas_detalhe_csv: Path, 
                 gemini_api_key: str,
                 progress_callback: Optional[Callable[[float], None]] = None,
                 cancel_event: Optional[threading.Event] = None) -> List[str]:
    """
    Processa os PDFs não analisados e salva os resultados nos arquivos CSV.
    Retorna uma lista de IDs de PDFs que falharam na análise.
    """
    processed_ids = set()
    failed_pdf_ids = [] # List to store IDs of PDFs that failed processing
    operation_logger = get_logger("pdf_processing")
    
    try:
        # Read existing summary data
        if jogos_resumo_csv.exists():
            summary_data = read_csv(jogos_resumo_csv)
            for row in summary_data:
                jogo_id = row.get("id_jogo_cbf")
                if jogo_id:
                    processed_ids.add(str(jogo_id))
            operation_logger.info("Loaded processed IDs", count=len(processed_ids), csv_file=str(jogos_resumo_csv))
    except Exception as e:
        handle_error(
            error=e, 
            log_context={"csv_file": str(jogos_resumo_csv)},
            log_level="warning"
        )

    pdf_files = [f for f in pdf_dir.iterdir() if f.is_file() and f.suffix == ".pdf"]
    operation_logger.info("Found PDF files", count=len(pdf_files), directory=str(pdf_dir))
    
    total_pdfs = len(pdf_files)
    if total_pdfs == 0:
        if progress_callback:
            progress_callback(100.0)
        return []


    for idx, pdf_file_path_obj in enumerate(pdf_files):
        if cancel_event and cancel_event.is_set():
            operation_logger.info("PDF processing cancelled by user.")
            raise OperationCancelledError("Processamento de PDF cancelado.")

        pdf_file = pdf_file_path_obj.name
        id_jogo_cbf = str(pdf_file_path_obj.stem) # Use stem to get filename without extension

        if id_jogo_cbf in processed_ids:
            operation_logger.info("Skipping processed PDF", filename=pdf_file, id=id_jogo_cbf)
            if progress_callback:
                progress_callback(((idx + 1) / total_pdfs) * 100)
            continue

        operation_logger.info("Processing PDF", filename=pdf_file, id=id_jogo_cbf, path=str(pdf_file_path_obj))

        try:
            with open(pdf_file_path_obj, 'rb') as f:
                pdf_content_bytes = f.read()

            response = analyze_pdf(pdf_content_bytes, gemini_api_key) # Pass gemini_api_key
            
            # Cache successful responses
            if not response.get("error"):
                try:
                    cache_dir = Path("cache")
                    cache_dir.mkdir(exist_ok=True)
                    cache_file = cache_dir / f"{id_jogo_cbf}.json"
                    with open(cache_file, 'w', encoding='utf-8') as cf:
                        json.dump(response, cf)
                except Exception as cache_err:
                    operation_logger.warning("Failed to write cache file", error=str(cache_err), id_jogo_cbf=id_jogo_cbf)

            if response.get("error"):
                error_message = response.get("error")
                operation_logger.error("Error analyzing PDF with Gemini", 
                                      error=error_message, 
                                      filename=pdf_file, 
                                      id=id_jogo_cbf)
                failed_pdf_ids.append(id_jogo_cbf) # Add to failed list
                # Do not write to CSV here, will be reported at the end.
                # We still mark it as "processed" for this run to avoid retrying immediately
                processed_ids.add(id_jogo_cbf) 
                if progress_callback:
                    progress_callback(((idx + 1) / total_pdfs) * 100)
                continue # Skip to next PDF

            # ... (rest of the data extraction and CSV writing for successful analysis)
            match_details = response.get("match_details", {})
            financial_data = response.get("financial_data", {})
            audience_stats = response.get("audience_statistics", {})
            revenue_details = financial_data.get("revenue_details", [])
            expense_details = financial_data.get("expense_details", [])

            resumo_jogo = {
                "id_jogo_cbf": id_jogo_cbf,
                "data_jogo": match_details.get("match_date"),
                "time_mandante": match_details.get("home_team"),
                "time_visitante": match_details.get("away_team"),
                "estadio": match_details.get("stadium"),
                "competicao": match_details.get("competition"),
                "publico_pagante": audience_stats.get("paid_attendance"),
                "publico_nao_pagante": audience_stats.get("non_paid_attendance"),
                "publico_total": audience_stats.get("total_attendance"),
                "receita_bruta_total": financial_data.get("gross_revenue"),
                "despesa_total": financial_data.get("total_expenses"),
                "resultado_liquido": financial_data.get("net_result"),
                "caminho_pdf_local": str(pdf_file_path_obj),
                "data_processamento": datetime.date.today().isoformat(),
                "status": "Sucesso",
                "log_erro": None
            }
            
            jogos_resumo_headers = [
                "id_jogo_cbf", "data_jogo", "time_mandante", "time_visitante", "estadio", "competicao",
                "publico_pagante", "publico_nao_pagante", "publico_total",
                "receita_bruta_total", "despesa_total", "resultado_liquido",
                "caminho_pdf_local", "data_processamento", "status", "log_erro"
            ]
            validated_summary = validate_summary([resumo_jogo])
            append_to_csv(jogos_resumo_csv, validated_summary, jogos_resumo_headers)

            for item in revenue_details:
                item["id_jogo_cbf"] = id_jogo_cbf
            for item in expense_details:
                item["id_jogo_cbf"] = id_jogo_cbf

            if revenue_details:
                receita_headers = ["id_jogo_cbf"] + [k for k in revenue_details[0].keys() if k != "id_jogo_cbf"]
                validated_revenue = validate_revenue(revenue_details)
                append_to_csv(receitas_detalhe_csv, validated_revenue, receita_headers)

            if expense_details:
                despesa_headers = ["id_jogo_cbf"] + [k for k in expense_details[0].keys() if k != "id_jogo_cbf"]
                validated_expense = validate_expense(expense_details)
                append_to_csv(despesas_detalhe_csv, validated_expense, despesa_headers)

            operation_logger.info("Successfully processed PDF", 
                                 id=id_jogo_cbf, 
                                 match_date=match_details.get("match_date"),
                                 teams=f"{match_details.get('home_team')} vs {match_details.get('away_team')}")
            processed_ids.add(id_jogo_cbf)

        except FileNotFoundError:
            handle_error(
                error=FileNotFoundError(f"PDF file not found: {str(pdf_file_path_obj)}"),
                log_context={"id": id_jogo_cbf, "filename": pdf_file},
                log_level="error"
            )
            failed_pdf_ids.append(id_jogo_cbf) # Also count as failed
        except IOError as io_err:
            handle_error(
                error=io_err,
                log_context={"id": id_jogo_cbf, "filename": pdf_file, "path": str(pdf_file_path_obj)},
                log_level="error"
            )
            failed_pdf_ids.append(id_jogo_cbf)
        except OperationCancelledError: # Re-raise to be caught by threaded_operation
            raise
        except Exception as e:
            error_details = handle_error(
                error=e,
                log_context={"id": id_jogo_cbf, "filename": pdf_file, "path": str(pdf_file_path_obj)},
                log_level="error"
            )
            failed_pdf_ids.append(id_jogo_cbf)
            # Log error to CSV with a generic "Erro Inesperado" if needed, or rely on failed_pdf_ids list
            # For now, we are not writing specific error rows for these unexpected errors to jogos_resumo.csv
            # as the primary goal is to report them via failed_pdf_ids.
            # If an error row is still desired:
            # error_log_entry = { ... "status": "Erro Inesperado", "log_erro": str(e) ... }
            # append_to_csv(jogos_resumo_csv, [error_log_entry], error_log_entry.keys())
            processed_ids.add(id_jogo_cbf) # Mark as processed to avoid re-attempt in same run

        if progress_callback:
            progress_callback(((idx + 1) / total_pdfs) * 100)
            
    return failed_pdf_ids # Return the list of failed PDF IDs

def overwrite_row_in_csv(file_path, new_row, key_field):
    """
    Overwrites a row in a CSV file based on a key field. If the key exists, the row is replaced; otherwise, it is appended.
    """
    import csv
    from pathlib import Path
    file_path = Path(file_path)
    rows = []
    found = False
    if file_path.exists():
        with open(file_path, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                if row.get(key_field) == new_row.get(key_field):
                    rows.append(new_row)
                    found = True
                else:
                    rows.append(row)
    if not found:
        # If not found, append
        if not rows:
            headers = list(new_row.keys())
        rows.append(new_row)
    # Write all rows back
    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

def reprocess_all_pdfs(pdf_dir, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key):
    """
    Processes all PDFs and overwrites the corresponding rows in the CSVs.
    Only updates jogos_resumo_csv (summary), ignores details.
    """
    from .validation import validate_summary
    import datetime
    from .gemini import analyze_pdf
    from pathlib import Path
    pdf_dir = Path(pdf_dir)
    jogos_resumo_csv = Path(jogos_resumo_csv)
    pdf_files = [f for f in pdf_dir.iterdir() if f.is_file() and f.suffix == ".pdf"]
    for pdf_file_path_obj in pdf_files:
        id_jogo_cbf = str(pdf_file_path_obj.stem)
        try:
            with open(pdf_file_path_obj, 'rb') as f:
                pdf_content_bytes = f.read()
            response = analyze_pdf(pdf_content_bytes, gemini_api_key)
            match_details = response.get("match_details", {})
            financial_data = response.get("financial_data", {})
            audience_stats = response.get("audience_statistics", {})
            resumo_jogo = {
                "id_jogo_cbf": id_jogo_cbf,
                "data_jogo": match_details.get("match_date"),
                "time_mandante": match_details.get("home_team"),
                "time_visitante": match_details.get("away_team"),
                "estadio": match_details.get("stadium"),
                "competicao": match_details.get("competition"),
                "publico_pagante": audience_stats.get("paid_attendance"),
                "publico_nao_pagante": audience_stats.get("non_paid_attendance"),
                "publico_total": audience_stats.get("total_attendance"),
                "receita_bruta_total": financial_data.get("gross_revenue"),
                "despesa_total": financial_data.get("total_expenses"),
                "resultado_liquido": financial_data.get("net_result"),
                "caminho_pdf_local": str(pdf_file_path_obj),
                "data_processamento": datetime.date.today().isoformat(),
                "status": "Sucesso",
                "log_erro": None
            }
            jogos_resumo_headers = [
                "id_jogo_cbf", "data_jogo", "time_mandante", "time_visitante", "estadio", "competicao",
                "publico_pagante", "publico_nao_pagante", "publico_total",
                "receita_bruta_total", "despesa_total", "resultado_liquido",
                "caminho_pdf_local", "data_processamento", "status", "log_erro"
            ]
            validated_summary = validate_summary([resumo_jogo])[0]
            overwrite_row_in_csv(jogos_resumo_csv, validated_summary, "id_jogo_cbf")
        except Exception as e:
            print(f"Failed to process {pdf_file_path_obj}: {e}")

if __name__ == "__main__":
    main()