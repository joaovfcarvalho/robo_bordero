import streamlit as st
import pandas as pd
import numpy as np
import altair as alt # Added for custom chart sorting
from dotenv import load_dotenv
import datetime
from pathlib import Path
import os

# Load environment variables
load_dotenv()

st.set_page_config(layout="wide") # Moved to the top

# Admin password from environment variable (for security)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "cbf2025admin")

# Load data
@st.cache_data
def load_data():
    # Import database client
    from src.database import get_database_client
    import os

    # Check if required environment variables are set
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        st.error("⚠️ **Configuração Incompleta**")
        st.warning("""
        As variáveis de ambiente do Supabase não estão configuradas.

        **Para Railway:**
        1. Acesse o painel do Railway
        2. Selecione o serviço 'cbf-dashboard'
        3. Vá em 'Variables'
        4. Adicione as seguintes variáveis:
           - `SUPABASE_URL`: Sua URL do Supabase (exemplo: https://xxxxx.supabase.co)
           - `SUPABASE_KEY`: Sua chave anon do Supabase
           - `ANTHROPIC_API_KEY`: Sua chave da API do Claude (para funcionalidades admin)

        **Variáveis faltando:**
        """)
        missing_vars = []
        if not supabase_url:
            missing_vars.append("❌ SUPABASE_URL")
        else:
            missing_vars.append("✅ SUPABASE_URL")
        if not supabase_key:
            missing_vars.append("❌ SUPABASE_KEY")
        else:
            missing_vars.append("✅ SUPABASE_KEY")

        st.code("\n".join(missing_vars))
        st.info("Após configurar as variáveis, o Railway fará o redeploy automaticamente.")
        return pd.DataFrame()  # Return empty DataFrame

    try:
        # Get data from Supabase
        db = get_database_client()
        matches = db.get_all_matches(limit=10000)  # Adjust limit as needed

        # Convert to DataFrame
        data = pd.DataFrame(matches)

        # Check if data is empty
        if data.empty:
            st.warning("⚠️ Nenhum dado encontrado no Supabase. O banco de dados pode estar vazio.")
            st.info("""
            **Como resolver:**
            1. Execute o worker para processar borderôs e popular o banco de dados
            2. Ou aguarde o processamento automático dos PDFs
            """)
            return pd.DataFrame()  # Return empty DataFrame

        # Map database columns to dashboard expected columns
        # Database uses: receita_total, saldo
        # Dashboard expects: receita_bruta_total, resultado_liquido
        if 'receita_total' in data.columns:
            data['receita_bruta_total'] = data['receita_total']
        if 'saldo' in data.columns:
            data['resultado_liquido'] = data['saldo']

        # Use normalized names if available
        if 'time_mandante_normalizado' in data.columns:
            data['time_mandante'] = data['time_mandante_normalizado'].fillna(data.get('time_mandante', ''))
        if 'time_visitante_normalizado' in data.columns:
            data['time_visitante'] = data['time_visitante_normalizado'].fillna(data.get('time_visitante', ''))
        if 'estadio_normalizado' in data.columns:
            data['estadio'] = data['estadio_normalizado'].fillna(data.get('estadio', ''))

    except Exception as e:
        st.error(f"❌ Erro ao conectar ao Supabase: {str(e)}")
        st.info("Tentando carregar dados do CSV local como fallback...")

        # Fallback to CSV if Supabase fails
        try:
            data = pd.read_csv("csv/jogos_resumo_clean.csv")
            st.success("✅ Dados carregados do CSV local")
        except FileNotFoundError:
            st.error("Arquivo CSV também não encontrado.")
            st.info("""
            **Como resolver:**
            1. Configure as variáveis de ambiente do Supabase no Railway
            2. Ou execute o worker para gerar dados locais
            """)
            return pd.DataFrame()  # Return empty DataFrame

    # Explicitly convert 'data_jogo' to datetime, coercing errors to NaT
    if 'data_jogo' in data.columns:
        data['data_jogo'] = pd.to_datetime(data['data_jogo'], errors='coerce')
    else:
        st.warning("⚠️ Coluna 'data_jogo' não encontrada nos dados.")
        data['data_jogo'] = pd.Series(dtype='datetime64[ns]')

    # Ensure relevant columns are numeric, coercing errors to NaN
    numeric_cols = ['receita_bruta_total', 'publico_total', 'resultado_liquido']
    # Add 'estadio' to the list of columns to check for existence, though it's not numeric
    # We'll handle its specific processing later if needed.
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        else:
            # For essential numeric cols, we might want to raise an error or fill with 0
            # For now, let's assume they exist or handle missing data downstream
            pass


    # Calculate additional metrics
    if 'receita_bruta_total' in data.columns and 'publico_total' in data.columns:
        # Ensure publico_total is not zero to avoid division by zero
        data['ticket_medio'] = np.where(data['publico_total'] != 0, data['receita_bruta_total'] / data['publico_total'], 0)
    else:
        data['ticket_medio'] = 0
        
    if 'resultado_liquido' in data.columns and 'receita_bruta_total' in data.columns:
        # Ensure receita_bruta_total is not zero to avoid division by zero
        data['margem_liquida'] = np.where(data['receita_bruta_total'] != 0, data['resultado_liquido'] / data['receita_bruta_total'], 0)
    else:
        data['margem_liquida'] = 0
    
    # Replace inf values with NaN, then fill NaN with 0 (or an appropriate value)
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    data['ticket_medio'].fillna(0, inplace=True)
    data['margem_liquida'].fillna(0, inplace=True)
    
    # Create Portuguese day of the week
    if 'data_jogo' in data.columns and not data['data_jogo'].isnull().all():
        dias_semana_map = {
            'Monday': 'Segunda-feira',
            'Tuesday': 'Terça-feira',
            'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira',
            'Friday': 'Sexta-feira',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        data['dia_semana_en'] = data['data_jogo'].dt.day_name()
        data['dia_semana_pt'] = data['dia_semana_en'].map(dias_semana_map)
        
        # Define categorical order for Portuguese days of the week
        dias_ordenados = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        data['dia_semana_pt'] = pd.Categorical(data['dia_semana_pt'], categories=dias_ordenados, ordered=True)
    else:
        data['dia_semana_pt'] = pd.Series(dtype='category')


    # Check for 'estadio' column and clean it (example: fill NaN with 'Desconhecido')
    if 'estadio' not in data.columns:
        # If 'estadio' column doesn't exist, create it and fill with a placeholder
        # This allows the rest of the dashboard to function without breaking,
        # and stadium-specific sections will indicate no data or use the placeholder.
        data['estadio'] = 'Estádio Desconhecido'
        st.sidebar.warning("Coluna 'estadio' não encontrada no arquivo CSV. Análises por estádio serão limitadas.")
    else:
        # If 'estadio' column exists, fill any NaN values
        data['estadio'] = data['estadio'].fillna('Desconhecido')

    return data

data = load_data()

st.title("CBF Robot - Análise de Jogos de Futebol")

# Check if data is empty and show setup instructions
if data.empty:
    st.warning("""
    ### 📋 Dashboard não configurado

    O dashboard precisa de dados para funcionar. Siga os passos abaixo:

    #### 🔧 Configuração do Railway:
    1. Acesse o [Railway Dashboard](https://railway.app/dashboard)
    2. Selecione seu projeto
    3. Clique no serviço **cbf-dashboard**
    4. Vá em **Variables**
    5. Adicione as variáveis de ambiente necessárias (veja acima)

    #### ℹ️ Informações importantes:
    - Após configurar as variáveis, o Railway fará redeploy automaticamente
    - O processo de deploy leva cerca de 2-5 minutos
    - Recarregue a página após o deploy completar

    #### 📖 Documentação:
    - [Guia de Deploy](https://github.com/joaovfcarvalho/robo_bordero#readme)
    - [Configuração do Supabase](https://supabase.com/docs)
    """)
    st.stop()  # Stop execution here if no data

# --- FILTERS ---
st.sidebar.header("Filtros")

# Date range filter
if 'data_jogo' in data.columns and not data['data_jogo'].isnull().all():
    min_date = data['data_jogo'].min()
    max_date = data['data_jogo'].max()

    if pd.isna(min_date) or pd.isna(max_date):
        st.sidebar.warning("Datas de jogos não disponíveis para criar o filtro de período.")
        from datetime import datetime
        min_date_dt = datetime(2020, 1, 1)
        max_date_dt = datetime.now()
    else:
        min_date_dt = min_date.to_pydatetime()
        max_date_dt = max_date.to_pydatetime()
        
    default_start_date = max_date_dt.replace(month=1, day=1) if max_date_dt.year > min_date_dt.year else min_date_dt
    default_end_date = max_date_dt

    selected_date_range = st.sidebar.slider(
        "Período do Jogo",
        min_value=min_date_dt,
        max_value=max_date_dt,
        value=(default_start_date, default_end_date),
        format="DD/MM/YYYY"
    )
    start_date_filter = pd.Timestamp(selected_date_range[0])
    end_date_filter = pd.Timestamp(selected_date_range[1])
    data_filtrada_periodo = data[
        (data['data_jogo'] >= start_date_filter) & (data['data_jogo'] <= end_date_filter)
    ].copy()
else:
    st.sidebar.warning("Coluna 'data_jogo' não encontrada ou vazia. Filtro de período desabilitado.")
    data_filtrada_periodo = data.copy()


# Competition filter
all_competitions_label = "Todas as Competições"
if 'competicao' in data_filtrada_periodo.columns:
    competicao_options = sorted(data_filtrada_periodo["competicao"].dropna().unique())
else:
    competicao_options = []
    st.sidebar.warning("Coluna 'competicao' não encontrada. Filtro de competição desabilitado.")

competicao_selecionada_single = st.sidebar.selectbox(
    "Competição",
    options=[all_competitions_label] + competicao_options,
    index=0
)

# Home team filter
all_teams_label = "Todos os Times"
if 'time_mandante' in data_filtrada_periodo.columns:
    times_mandantes_options = sorted(data_filtrada_periodo["time_mandante"].dropna().unique())
else:
    times_mandantes_options = []
    st.sidebar.warning("Coluna 'time_mandante' não encontrada. Filtro de time mandante desabilitado.")

time_mandante_selecionado_single = st.sidebar.selectbox(
    "Time Mandante",
    options=[all_teams_label] + times_mandantes_options,
    index=0 
)

# Away team filter
if 'time_visitante' in data_filtrada_periodo.columns:
    times_visitantes_options = sorted(data_filtrada_periodo["time_visitante"].dropna().unique())
else:
    times_visitantes_options = []
    st.sidebar.warning("Coluna 'time_visitante' não encontrada. Filtro de time visitante desabilitado.")
    
time_visitante_selecionado_single = st.sidebar.selectbox(
    "Time Visitante",
    options=[all_teams_label] + times_visitantes_options,
    index=0
)

# Stadium filter
all_stadiums_label = "Todos os Estádios"
if 'estadio' in data_filtrada_periodo.columns:
    estadio_options = sorted(data_filtrada_periodo["estadio"].dropna().unique())
else:
    estadio_options = [] # Should be handled by load_data creating a default 'estadio' column
    # Warning already given in load_data if 'estadio' was missing initially

estadio_selecionado_single = st.sidebar.selectbox(
    "Estádio",
    options=[all_stadiums_label] + estadio_options,
    index=0
)

# --- ADMIN SECTION ---
st.sidebar.markdown("---")
st.sidebar.header("🔒 Opções Admin")

# Initialize session state for admin authentication
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

# Admin authentication
if not st.session_state.admin_authenticated:
    admin_password_input = st.sidebar.text_input("Senha Admin:", type="password", key="admin_password")
    if st.sidebar.button("Entrar"):
        if admin_password_input == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.sidebar.success("✅ Autenticado com sucesso!")
            st.rerun()
        else:
            st.sidebar.error("❌ Senha incorreta!")
else:
    st.sidebar.success("✅ Admin autenticado")

    # Admin operations
    st.sidebar.subheader("Operações Administrativas")

    # WARNING: Railway has ephemeral filesystem - files created here won't persist across deploys
    st.sidebar.warning("⚠️ **Aviso Railway**: Arquivos PDFs/CSVs gerados aqui são temporários e serão perdidos no próximo deploy. Use Supabase para persistência.")

    # Routine Running Option
    if st.sidebar.button("🚀 Executar Rotina Completa", help="Download de todos os borderôs restantes e processamento com LLM"):
        try:
            from src.config_manager import get_config_manager
            from src.scraper import download_pdfs
            from src.main import process_pdfs

            # Get configurations
            config_manager = get_config_manager()
            api_key = config_manager.get_anthropic_key()

            if not api_key:
                st.sidebar.error("❌ Chave API Claude não configurada!")
            else:
                # Default settings
                current_year = datetime.date.today().year
                competitions = ["142", "424", "242"]  # Default competitions
                pdf_dir = Path("pdfs")
                csv_dir = Path("csv")

                # Create directories if needed
                pdf_dir.mkdir(exist_ok=True)
                csv_dir.mkdir(exist_ok=True)

                # Progress tracking
                progress_bar = st.sidebar.progress(0)
                status_text = st.sidebar.empty()

                # Step 1: Download PDFs
                status_text.text("📥 Baixando borderôs...")
                total_steps = len(competitions) + 1
                for idx, competition in enumerate(competitions):
                    progress_bar.progress((idx) / total_steps)
                    status_text.text(f"📥 Baixando competição {competition}...")
                    download_pdfs(current_year, competition, str(pdf_dir))

                # Step 2: Process PDFs
                progress_bar.progress(len(competitions) / total_steps)
                status_text.text("🤖 Processando borderôs com LLM...")

                jogos_resumo_csv = csv_dir / "jogos_resumo.csv"
                receitas_detalhe_csv = csv_dir / "receitas_detalhe.csv"
                despesas_detalhe_csv = csv_dir / "despesas_detalhe.csv"

                failed_pdfs = process_pdfs(pdf_dir, jogos_resumo_csv, receitas_detalhe_csv,
                                          despesas_detalhe_csv, api_key)

                # Complete
                progress_bar.progress(1.0)
                if failed_pdfs:
                    status_text.text(f"⚠️ Concluído com {len(failed_pdfs)} erros")
                    st.sidebar.warning(f"PDFs com falha: {', '.join(failed_pdfs)}")
                else:
                    status_text.text("✅ Rotina completa executada!")
                    st.sidebar.success("✅ Todos os borderôs foram processados!")

                st.cache_data.clear()  # Clear cache to reload data
                st.balloons()

        except Exception as e:
            st.sidebar.error(f"❌ Erro ao executar rotina: {str(e)}")
            import traceback
            st.sidebar.code(traceback.format_exc())

    # Test Specific Document Option
    st.sidebar.markdown("---")
    st.sidebar.subheader("Testar Documento Específico")
    test_doc_id = st.sidebar.text_input("ID do Jogo (nome do PDF sem extensão):", key="test_doc_id")

    # Initialize session state for test results
    if 'test_result' not in st.session_state:
        st.session_state.test_result = None

    if st.sidebar.button("🧪 Processar Documento de Teste"):
        if not test_doc_id:
            st.sidebar.warning("⚠️ Por favor, insira o ID do documento.")
        else:
            try:
                from src.claude import ClaudeClient
                from src.config_manager import get_config_manager

                # Get API key
                config_manager = get_config_manager()
                api_key = config_manager.get_anthropic_key()

                if not api_key:
                    st.sidebar.error("❌ Chave API Claude não configurada!")
                else:
                    # Find and process the PDF
                    pdf_path = Path("pdfs") / f"{test_doc_id}.pdf"

                    if not pdf_path.exists():
                        st.sidebar.error(f"❌ PDF não encontrado: {pdf_path}")
                    else:
                        with st.spinner(f"Processando documento {test_doc_id}..."):
                            # Read PDF
                            with open(pdf_path, 'rb') as f:
                                pdf_bytes = f.read()

                            # Analyze with Claude
                            client = ClaudeClient(api_key=api_key)
                            result = client.analyze_pdf(pdf_bytes)

                            if result.get("success"):
                                # Store result in session state
                                st.session_state.test_result = {
                                    'doc_id': test_doc_id,
                                    'data': result.get("data", {}),
                                    'pdf_path': str(pdf_path)
                                }
                                st.sidebar.success("✅ Documento processado com sucesso!")
                            else:
                                st.sidebar.error(f"❌ Erro no processamento: {result.get('error')}")
                                st.session_state.test_result = None

            except Exception as e:
                st.sidebar.error(f"❌ Erro ao processar documento: {str(e)}")
                import traceback
                st.sidebar.code(traceback.format_exc())
                st.session_state.test_result = None

    # Display test results if available
    if st.session_state.test_result:
        with st.sidebar.expander("📊 Resultados do Teste", expanded=True):
            st.json(st.session_state.test_result['data'])

        # Save to CSV button
        if st.sidebar.button("💾 Salvar Resultado no CSV"):
            try:
                from src.db import append_to_csv
                from src.validation import validate_summary

                data = st.session_state.test_result['data']
                match_details = data.get("match_details", {})
                financial_data = data.get("financial_data", {})
                audience_stats = data.get("audience_statistics", {})
                doc_id = st.session_state.test_result['doc_id']
                pdf_path = st.session_state.test_result['pdf_path']

                resumo_jogo = {
                    "id_jogo_cbf": doc_id,
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
                    "caminho_pdf_local": pdf_path,
                    "data_processamento": datetime.date.today().isoformat(),
                    "status": "Sucesso",
                    "log_erro": None
                }

                csv_path = Path("csv") / "jogos_resumo.csv"
                headers = list(resumo_jogo.keys())
                validated = validate_summary([resumo_jogo])
                append_to_csv(csv_path, validated, headers)

                st.sidebar.success("💾 Salvo no CSV!")
                st.session_state.test_result = None  # Clear result after saving
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"❌ Erro ao salvar: {str(e)}")
                import traceback
                st.sidebar.code(traceback.format_exc())

    # Logout button
    if st.sidebar.button("🚪 Sair (Admin)"):
        st.session_state.admin_authenticated = False
        st.rerun()

st.sidebar.markdown("---")


# Apply filters
data_dashboard = data_filtrada_periodo.copy()

if 'competicao' in data_dashboard.columns and competicao_selecionada_single != all_competitions_label:
    data_dashboard = data_dashboard[data_dashboard["competicao"] == competicao_selecionada_single]
if 'time_mandante' in data_dashboard.columns and time_mandante_selecionado_single != all_teams_label:
    data_dashboard = data_dashboard[data_dashboard["time_mandante"] == time_mandante_selecionado_single]
if 'time_visitante' in data_dashboard.columns and time_visitante_selecionado_single != all_teams_label:
    data_dashboard = data_dashboard[data_dashboard["time_visitante"] == time_visitante_selecionado_single]
if 'estadio' in data_dashboard.columns and estadio_selecionado_single != all_stadiums_label:
    data_dashboard = data_dashboard[data_dashboard["estadio"] == estadio_selecionado_single]


if data_dashboard.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    # --- GENERAL STATS ---
    st.header("Estatísticas Gerais do Período Filtrado")
    total_jogos = data_dashboard.shape[0]
    total_publico = data_dashboard['publico_total'].sum() if 'publico_total' in data_dashboard.columns else 0
    total_receita = data_dashboard['receita_bruta_total'].sum() if 'receita_bruta_total' in data_dashboard.columns else 0
    
    overall_ticket_medio = (total_receita / total_publico) if total_publico > 0 else 0
    overall_resultado_liquido = data_dashboard['resultado_liquido'].sum() if 'resultado_liquido' in data_dashboard.columns else 0
    overall_margem_liquida = (overall_resultado_liquido / total_receita) if total_receita > 0 else 0
    total_receita_milhoes = total_receita / 1_000_000

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total de Jogos", f"{total_jogos:,}")
    col2.metric("Público Total", f"{total_publico:,.0f}")
    col3.metric("Receita Bruta Total", f"R$ {total_receita_milhoes:,.2f}M")
    col4.metric("Ticket Médio Geral", f"R$ {overall_ticket_medio:,.2f}")
    col5.metric("Margem Líquida Média", f"{overall_margem_liquida:.2%}")

    st.markdown("---")

    # --- RESUMO POR COMPETIÇÃO ---
    if 'competicao' in data_dashboard.columns:
        st.header("Resumo por Competição")
        resumo_competicao_df = data_dashboard.groupby('competicao', observed=False).agg(
            total_jogos=('competicao', 'size'),
            publico_total=('publico_total', 'sum'),
            publico_medio=('publico_total', 'mean'),
            receita_bruta_total=('receita_bruta_total', 'sum'),
            # Ensure ticket_medio is treated as numeric before aggregation
            ticket_medio=('ticket_medio', lambda x: pd.to_numeric(x, errors='coerce').mean()),
            margem_liquida_media=('margem_liquida', lambda x: pd.to_numeric(x, errors='coerce').mean())
        ).reset_index()

        resumo_competicao_df.columns = [
            'Competição', 'Total de Jogos', 'Público Total', 'Público Médio', 
            'Receita Bruta Total', 'Ticket Médio', 'Margem Líquida Média'
        ]
        
        # Formatting for display
        formatted_resumo_competicao = resumo_competicao_df.style.format({
            'Público Total': '{:,.0f}',
            'Público Médio': '{:,.0f}',
            'Receita Bruta Total': lambda x: f"R$ {x/1_000_000:,.2f}M" if (isinstance(x, (int, float)) and pd.notnull(x)) else '-',
            'Ticket Médio': 'R$ {:,.2f}',
            'Margem Líquida Média': '{:.2%}'
        })
        st.dataframe(formatted_resumo_competicao, use_container_width=True)
        st.markdown("---")
    else:
        st.info("Dados de competição não disponíveis para o resumo.")


    # --- ATTENDANCE ANALYSIS ---
    st.header("Análise de Público")
    # col1_publico, col2_publico = st.columns(2) # Original, col2 was histogram
    col1_publico, col3_publico, col4_publico = st.columns(3) # Adjusted for 3 charts

    with col1_publico:
        if 'dia_semana_pt' in data_dashboard.columns and not data_dashboard['dia_semana_pt'].isnull().all() and 'publico_total' in data_dashboard.columns:
            st.subheader("Público Médio por Dia da Semana")
            # Ensure publico_total is numeric for groupby operation
            dia_semana_publico_series = data_dashboard.groupby('dia_semana_pt', observed=False)['publico_total'].mean()
            if not dia_semana_publico_series.empty:
                dia_semana_publico_df = dia_semana_publico_series.reset_index()
                dia_semana_publico_df.columns = ['Dia da Semana', 'Público Médio']
                
                chart = alt.Chart(dia_semana_publico_df).mark_bar().encode(
                    x=alt.X('Dia da Semana:N', sort=None),
                    y=alt.Y('Público Médio:Q', title='Público Médio'),
                    tooltip=['Dia da Semana', alt.Tooltip('Público Médio:Q', format=',.0f')]
                ).properties(
                    title='Público Médio por Dia da Semana'
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("Público médio por dia da semana, ordenado por dia.")
            else:
                st.info("Não há dados suficientes para o gráfico de público por dia da semana.")
        else:
            st.info("Dados de dia da semana não disponíveis.")

    # REMOVED: Histogram (was col2_publico)

    with col3_publico: # Was col3_publico
        if 'time_mandante' in data_dashboard.columns and 'publico_total' in data_dashboard.columns:
            st.subheader("Público Médio (Mandante)")
            # Ensure publico_total is numeric for groupby operation
            publico_medio_mandante_series = data_dashboard.groupby('time_mandante')['publico_total'].mean().sort_values(ascending=False).head(15)
            if not publico_medio_mandante_series.empty:
                publico_medio_mandante_df = publico_medio_mandante_series.reset_index()
                publico_medio_mandante_df.columns = ['Time Mandante', 'Público Médio']
                chart = alt.Chart(publico_medio_mandante_df).mark_bar().encode(
                    x=alt.X('Time Mandante:N', sort='-y', title='Time Mandante'),
                    y=alt.Y('Público Médio:Q', title='Público Médio'),
                    tooltip=['Time Mandante', alt.Tooltip('Público Médio:Q', format=',.0f')]
                ).properties(
                    title='Top 15 Público Médio (Mandante)'
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("Top 15 times com maior público médio como mandantes.")
            else:
                st.info("Não há dados para o público médio por time mandante.")
        else:
            st.info("Dados de time mandante ou público não disponíveis.")

    with col4_publico: # Was col4_publico
        if 'time_visitante' in data_dashboard.columns and 'publico_total' in data_dashboard.columns:
            st.subheader("Público Médio (Visitante)")
            # Ensure publico_total is numeric for groupby operation
            publico_medio_visitante_series = data_dashboard.groupby('time_visitante')['publico_total'].mean().sort_values(ascending=False).head(15)
            if not publico_medio_visitante_series.empty:
                publico_medio_visitante_df = publico_medio_visitante_series.reset_index()
                publico_medio_visitante_df.columns = ['Time Visitante', 'Público Médio']
                chart = alt.Chart(publico_medio_visitante_df).mark_bar().encode(
                    x=alt.X('Time Visitante:N', sort='-y', title='Time Visitante'),
                    y=alt.Y('Público Médio:Q', title='Público Médio'),
                    tooltip=['Time Visitante', alt.Tooltip('Público Médio:Q', format=',.0f')]
                ).properties(
                    title='Top 15 Público Médio (Visitante)'
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("Top 15 times com maior público médio como visitantes.")
            else:
                st.info("Não há dados para o público médio por time visitante.")
        else:
            st.info("Dados de time visitante ou público não disponíveis.")
    
    st.markdown("---")

    # --- ANÁLISE POR ESTÁDIO ---
    if 'estadio' in data_dashboard.columns and data_dashboard['estadio'].nunique() > 0 and not (data_dashboard['estadio'].nunique() == 1 and data_dashboard['estadio'].iloc[0] in ['Estádio Desconhecido', 'Desconhecido']):
        st.header("Análise por Estádio")
        col1_estadio, col2_estadio = st.columns(2)

        with col1_estadio:
            if 'publico_total' in data_dashboard.columns:
                st.subheader("Público Médio por Estádio")
                # Ensure publico_total is numeric for groupby operation
                publico_medio_estadio_series = data_dashboard.groupby('estadio')['publico_total'].mean().sort_values(ascending=False).head(15)
                if not publico_medio_estadio_series.empty:
                    publico_medio_estadio_df = publico_medio_estadio_series.reset_index()
                    publico_medio_estadio_df.columns = ['Estádio', 'Público Médio']
                    chart = alt.Chart(publico_medio_estadio_df).mark_bar().encode(
                        x=alt.X('Estádio:N', sort='-y', title='Estádio'),
                        y=alt.Y('Público Médio:Q', title='Público Médio'),
                        tooltip=['Estádio', alt.Tooltip('Público Médio:Q', format=',.0f')]
                    ).properties(
                        title='Top 15 Público Médio por Estádio'
                    )
                    st.altair_chart(chart, use_container_width=True)
                    st.caption("Top 15 estádios com maior público médio.")
                else:
                    st.info("Não há dados suficientes para o público médio por estádio.")
        
        with col2_estadio:
            if 'ticket_medio' in data_dashboard.columns and 'estadio' in data_dashboard.columns:
                st.subheader("Ticket Médio por Estádio")
                
                # Filter for valid ticket data (not NaN and > 0) before grouping
                valid_ticket_data_estadio = data_dashboard[
                    data_dashboard['ticket_medio'].notna() & (data_dashboard['ticket_medio'] > 0)
                ]

                if not valid_ticket_data_estadio.empty:
                    ticket_medio_estadio_series = valid_ticket_data_estadio.groupby('estadio')['ticket_medio'].mean().sort_values(ascending=False).head(15)
                    # Check if the series is not empty AND not all NaN
                    if not ticket_medio_estadio_series.empty and not ticket_medio_estadio_series.isnull().all():
                        ticket_medio_estadio_df = ticket_medio_estadio_series.reset_index()
                        ticket_medio_estadio_df.columns = ['Estádio', 'Ticket Médio']
                        chart = alt.Chart(ticket_medio_estadio_df).mark_bar().encode(
                            x=alt.X('Estádio:N', sort='-y', title='Estádio'),
                            y=alt.Y('Ticket Médio:Q', title='Ticket Médio (R$)'),
                            tooltip=['Estádio', alt.Tooltip('Ticket Médio:Q', format=',.2f')]
                        ).properties(
                            title='Top 15 Ticket Médio por Estádio'
                        )
                        st.altair_chart(chart, use_container_width=True)
                        st.caption("Top 15 estádios com maior ticket médio.")
                    else:
                        st.info("Não há dados de ticket médio válidos (maiores que zero) para exibir no gráfico por estádio após o agrupamento.")
                else:
                    st.info("Não há dados de ticket médio válidos (maiores que zero) para calcular o ticket médio por estádio.")
            else:
                st.info("Dados de estádio ou ticket médio não disponíveis para o gráfico.")

        st.subheader("Estatísticas por Estádio (Filtrado)")
        # Ensure relevant columns are numeric before aggregation
        agg_functions = {
            'publico_total': lambda x: pd.to_numeric(x, errors='coerce').sum(),
            'publico_medio': lambda x: pd.to_numeric(x, errors='coerce').mean(),
            'receita_bruta_total': lambda x: pd.to_numeric(x, errors='coerce').sum(),
            'ticket_medio': lambda x: pd.to_numeric(x, errors='coerce').mean()
        }
        # Filter out columns not present in data_dashboard to prevent errors
        valid_agg_functions = {
            col: func for col, func in agg_functions.items() 
            if col.replace('_sum','').replace('_mean','') in data_dashboard.columns or col in data_dashboard.columns
        }

        # Dynamically build the aggregation dictionary
        agg_dict = {}
        if 'publico_total' in data_dashboard.columns:
            agg_dict['publico_total_sum'] = pd.NamedAgg(column='publico_total', aggfunc='sum')
            agg_dict['publico_total_mean'] = pd.NamedAgg(column='publico_total', aggfunc='mean')
        if 'receita_bruta_total' in data_dashboard.columns:
            agg_dict['receita_bruta_total_sum'] = pd.NamedAgg(column='receita_bruta_total', aggfunc='sum')
        if 'ticket_medio' in data_dashboard.columns:
            agg_dict['ticket_medio_mean'] = pd.NamedAgg(column='ticket_medio', aggfunc='mean')
        agg_dict['total_jogos_count'] = pd.NamedAgg(column='estadio', aggfunc='size')


        if agg_dict: # Proceed only if there's something to aggregate
            estadio_stats_df = data_dashboard.groupby('estadio', observed=False).agg(**agg_dict).reset_index()
            
            # Rename columns to be more friendly
            estadio_stats_df.rename(columns={
                'publico_total_sum': 'Público Total',
                'publico_total_mean': 'Público Médio',
                'receita_bruta_total_sum': 'Receita Bruta Total',
                'ticket_medio_mean': 'Ticket Médio',
                'total_jogos_count': 'Total de Jogos',
                'estadio': 'Estádio'
            }, inplace=True)

            # Reorder columns for display
            display_cols_estadio = ['Estádio', 'Total de Jogos', 'Público Total', 'Público Médio', 'Receita Bruta Total', 'Ticket Médio']
            # Filter for columns that actually exist in estadio_stats_df
            existing_display_cols_estadio = [col for col in display_cols_estadio if col in estadio_stats_df.columns]
            estadio_stats_df = estadio_stats_df[existing_display_cols_estadio]


            if 'Público Médio' in estadio_stats_df.columns:
                 estadio_stats_df = estadio_stats_df.sort_values(by='Público Médio', ascending=False)

            # Formatting
            formatters_estadio = {}
            if 'Público Total' in estadio_stats_df.columns: formatters_estadio['Público Total'] = '{:,.0f}'
            if 'Público Médio' in estadio_stats_df.columns: formatters_estadio['Público Médio'] = '{:,.0f}'
            if 'Receita Bruta Total' in estadio_stats_df.columns: formatters_estadio['Receita Bruta Total'] = lambda x: f"R$ {x/1_000_000:,.2f}M" if x != 0 else "R$ 0.00M"
            if 'Ticket Médio' in estadio_stats_df.columns: formatters_estadio['Ticket Médio'] = 'R$ {:,.2f}'
            
            if not estadio_stats_df.empty:
                st.dataframe(estadio_stats_df.style.format(formatters_estadio, na_rep='-'), use_container_width=True)
            else:
                st.info("Nenhuma estatística de estádio para exibir com os filtros atuais.")
        else:
            st.info("Colunas necessárias para estatísticas de estádio não estão disponíveis.")
        st.markdown("---")
    elif 'estadio' in data_dashboard.columns and (data_dashboard['estadio'].nunique() == 1 and data_dashboard['estadio'].iloc[0] in ['Estádio Desconhecido', 'Desconhecido']):
        st.info("Análise por estádio não disponível pois a coluna 'estadio' não foi encontrada ou contém apenas valores desconhecidos.")
    else: # Should not be reached if 'estadio' column is always created
        st.info("Dados de estádio não disponíveis para análise.")


    # --- FINANCIAL ANALYSIS ---
    st.header("Análise Financeira por Clube Mandante")
    col1_fin, col2_fin = st.columns(2)

    with col1_fin:
        if 'time_mandante' in data_dashboard.columns and 'ticket_medio' in data_dashboard.columns:
            st.subheader("Ticket Médio por Clube")
            
            # Filter for valid ticket data (not NaN and > 0) before grouping
            valid_ticket_data_clube = data_dashboard[
                data_dashboard['ticket_medio'].notna() & (data_dashboard['ticket_medio'] > 0)
            ]

            if not valid_ticket_data_clube.empty:
                ticket_medio_clube_series = valid_ticket_data_clube.groupby('time_mandante')['ticket_medio'].mean().sort_values(ascending=False).head(15)
                # Check if the series is not empty AND not all NaN
                if not ticket_medio_clube_series.empty and not ticket_medio_clube_series.isnull().all():
                    ticket_medio_clube_df = ticket_medio_clube_series.reset_index()
                    ticket_medio_clube_df.columns = ['Time Mandante', 'Ticket Médio']
                    chart = alt.Chart(ticket_medio_clube_df).mark_bar().encode(
                        x=alt.X('Time Mandante:N', sort='-y', title='Time Mandante'),
                        y=alt.Y('Ticket Médio:Q', title='Ticket Médio (R$)'),
                        tooltip=['Time Mandante', alt.Tooltip('Ticket Médio:Q', format=',.2f')]
                    ).properties(
                        title='Top 15 Ticket Médio (Mandante)'
                    )
                    st.altair_chart(chart, use_container_width=True)
                    st.caption("Top 15 times com maior ticket médio como mandantes.")
                else:
                    st.info("Não há dados de ticket médio válidos (maiores que zero) para exibir no gráfico por clube mandante após o agrupamento.")
            else:
                st.info("Não há dados de ticket médio válidos (maiores que zero) para calcular o ticket médio por clube mandante.")
        else:
            st.info("Dados de time mandante ou ticket médio não disponíveis para o gráfico.")

    with col2_fin:
        if 'time_mandante' in data_dashboard.columns and 'margem_liquida' in data_dashboard.columns:
            st.subheader("Margem Líquida Média por Clube")
            # Ensure margem_liquida is numeric for groupby operation
            margem_liquida_clube_series = data_dashboard.groupby('time_mandante')['margem_liquida'].mean().sort_values(ascending=False).head(15)
            if not margem_liquida_clube_series.empty:
                margem_liquida_clube_df = margem_liquida_clube_series.reset_index()
                margem_liquida_clube_df.columns = ['Time Mandante', 'Margem Líquida Média']
                chart = alt.Chart(margem_liquida_clube_df).mark_bar().encode(
                    x=alt.X('Time Mandante:N', sort='-y', title='Time Mandante'),
                    y=alt.Y('Margem Líquida Média:Q', axis=alt.Axis(format='.0%'), title='Margem Líquida Média'),
                    tooltip=['Time Mandante', alt.Tooltip('Margem Líquida Média:Q', format='.2%')]
                ).properties(
                    title='Top 15 Margem Líquida Média (Mandante)'
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("Top 15 times com maior margem líquida média como mandantes.")
            else:
                st.info("Não há dados para a margem líquida por clube mandante.")
        else:
            st.info("Dados de time mandante ou margem líquida não disponíveis.")
    
    # REMOVED: Bubble chart (Relação Público Total vs. Ticket Médio)
    st.markdown("---")
    
    # --- TOP 5 GAMES ---
    st.header("Top 5 Jogos por Diversas Métricas")
    # ... (rest of Top 5 games section remains largely the same, ensure columns exist)
    # Example for one, apply similar checks for others:
    if 'publico_total' in data_dashboard.columns and 'data_jogo' in data_dashboard.columns and \
       'time_mandante' in data_dashboard.columns and 'time_visitante' in data_dashboard.columns and \
       'competicao' in data_dashboard.columns:
        
        col1_top, col2_top = st.columns(2)
        col3_top, col4_top = st.columns(2)

        with col1_top:
            st.subheader("Por Maior Público Total")
            top_publico = data_dashboard.nlargest(5, 'publico_total')[
                ['data_jogo', 'time_mandante', 'time_visitante', 'publico_total', 'competicao', 'estadio']
            ]
            top_publico_display = top_publico.copy()
            top_publico_display['data_jogo'] = top_publico_display['data_jogo'].dt.strftime('%d/%m/%y')
            top_publico_display['publico_total'] = pd.to_numeric(top_publico_display['publico_total'], errors='coerce')
            st.dataframe(top_publico_display.style.format({"publico_total": "{:,.0f}"}, na_rep='-'), use_container_width=True)
        
        if 'receita_bruta_total' in data_dashboard.columns:
            with col2_top:
                st.subheader("Por Maior Receita Bruta")
                # Ensure 'receita_bruta_total' is numeric before nlargest
                data_dashboard['receita_bruta_total'] = pd.to_numeric(data_dashboard['receita_bruta_total'], errors='coerce')
                top_receita_cols = ['data_jogo', 'time_mandante', 'time_visitante', 'receita_bruta_total', 'competicao', 'estadio']
                # Filter for columns that actually exist
                existing_top_receita_cols = [col for col in top_receita_cols if col in data_dashboard.columns]
                
                if 'receita_bruta_total' in existing_top_receita_cols: # Check if the primary sort column exists
                    top_receita = data_dashboard.nlargest(5, 'receita_bruta_total')[existing_top_receita_cols]
                    top_receita_display = top_receita.copy()
                    if 'data_jogo' in top_receita_display.columns:
                        top_receita_display['data_jogo'] = top_receita_display['data_jogo'].dt.strftime('%d/%m/%y')
                    if 'receita_bruta_total' in top_receita_display.columns:
                        top_receita_display['receita_bruta_total'] = pd.to_numeric(top_receita_display['receita_bruta_total'], errors='coerce')
                    receita_formatters = {}
                    if 'receita_bruta_total' in top_receita_display.columns:
                        receita_formatters['receita_bruta_total'] = "R$ {:,.2f}"
                    st.dataframe(top_receita_display.style.format(receita_formatters, na_rep='-'), use_container_width=True)
                else:
                    st.info("Coluna 'receita_bruta_total' não disponível para Top 5.")
        else:
            with col2_top: st.info("Dados de receita bruta não disponíveis para Top 5.")

        if 'ticket_medio' in data_dashboard.columns and 'publico_total' in data_dashboard.columns:
            with col3_top:
                st.subheader("Por Maior Ticket Médio")
                # Ensure 'ticket_medio' and 'publico_total' are numeric
                data_dashboard['ticket_medio'] = pd.to_numeric(data_dashboard['ticket_medio'], errors='coerce')
                data_dashboard['publico_total'] = pd.to_numeric(data_dashboard['publico_total'], errors='coerce')

                top_ticket_cols = ['data_jogo', 'time_mandante', 'time_visitante', 'ticket_medio', 'publico_total', 'competicao', 'estadio']
                existing_top_ticket_cols = [col for col in top_ticket_cols if col in data_dashboard.columns]

                if 'ticket_medio' in existing_top_ticket_cols and 'publico_total' in existing_top_ticket_cols:
                    # Filter out games with zero or NaN public to avoid misleading high ticket_medio
                    valid_ticket_data = data_dashboard[data_dashboard['publico_total'] > 0]
                    if not valid_ticket_data.empty:
                        top_ticket = valid_ticket_data.nlargest(5, 'ticket_medio')[existing_top_ticket_cols]
                        top_ticket_display = top_ticket.copy()
                        if 'data_jogo' in top_ticket_display.columns:
                            top_ticket_display['data_jogo'] = top_ticket_display['data_jogo'].dt.strftime('%d/%m/%y')
                        ticket_formatters = {}
                        if 'ticket_medio' in top_ticket_display.columns:
                            ticket_formatters['ticket_medio'] = "R$ {:,.2f}"
                        if 'publico_total' in top_ticket_display.columns:
                            ticket_formatters['publico_total'] = "{:,.0f}"
                        st.dataframe(top_ticket_display.style.format(ticket_formatters, na_rep='-'), use_container_width=True)
                    else:
                        st.info("Não há dados válidos (com público > 0) para o Top 5 de Ticket Médio.")
                else:
                    st.info("Colunas 'ticket_medio' ou 'publico_total' não disponíveis para Top 5.")
        else:
            with col3_top: st.info("Dados de ticket médio ou público não disponíveis para Top 5.")

        if 'margem_liquida' in data_dashboard.columns and 'receita_bruta_total' in data_dashboard.columns:
            with col4_top:
                st.subheader("Por Maior Margem Líquida")
                # Ensure 'margem_liquida' and 'receita_bruta_total' are numeric
                data_dashboard['margem_liquida'] = pd.to_numeric(data_dashboard['margem_liquida'], errors='coerce')
                data_dashboard['receita_bruta_total'] = pd.to_numeric(data_dashboard['receita_bruta_total'], errors='coerce')

                top_margem_cols = ['data_jogo', 'time_mandante', 'time_visitante', 'margem_liquida', 'receita_bruta_total', 'competicao', 'estadio']
                existing_top_margem_cols = [col for col in top_margem_cols if col in data_dashboard.columns]

                if 'margem_liquida' in existing_top_margem_cols and 'receita_bruta_total' in existing_top_margem_cols:
                    # Filter out games with zero revenue to avoid misleading high margem_liquida
                    valid_margem_data = data_dashboard[data_dashboard['receita_bruta_total'] != 0]
                    if not valid_margem_data.empty:
                        top_margem = valid_margem_data.nlargest(5, 'margem_liquida')[existing_top_margem_cols]
                        top_margem_display = top_margem.copy()
                        if 'data_jogo' in top_margem_display.columns:
                            top_margem_display['data_jogo'] = top_margem_display['data_jogo'].dt.strftime('%d/%m/%y')
                        margem_formatters = {}
                        if 'margem_liquida' in top_margem_display.columns:
                            margem_formatters['margem_liquida'] = "{:.2%}"
                        if 'receita_bruta_total' in top_margem_display.columns:
                            margem_formatters['receita_bruta_total'] = "R$ {:,.2f}"
                        st.dataframe(top_margem_display.style.format(margem_formatters, na_rep='-'), use_container_width=True)
                    else:
                        st.info("Não há dados válidos (com receita != 0) para o Top 5 de Margem Líquida.")
                else:
                    st.info("Colunas 'margem_liquida' ou 'receita_bruta_total' não disponíveis para Top 5.")
        else:
            with col4_top: st.info("Dados de margem líquida ou receita não disponíveis para Top 5.")
        st.markdown("---")
    else:
        st.info("Dados insuficientes para a seção 'Top 5 Jogos'.")


    # Display raw data
    st.header("Dados Brutos Filtrados")
    st.write(f"Exibindo {data_dashboard.shape[0]} jogos.")
    
    data_display_cols = [
        'data_jogo', 'competicao', 'time_mandante', 'time_visitante', 'estadio', 
        'publico_total', 'ticket_medio', 'receita_bruta_total', 'margem_liquida',
        'publico_pagante', 'publico_nao_pagante', 'despesa_total', 'resultado_liquido'
    ]
    # Filter for columns that actually exist in data_dashboard
    existing_display_cols = [col for col in data_display_cols if col in data_dashboard.columns]
    data_display = data_dashboard[existing_display_cols].copy()
    formatters = {
        'data_jogo': lambda x: x.strftime('%d/%m/%y') if pd.notnull(x) else '',
        'publico_pagante': '{:,.0f}',
        'publico_nao_pagante': '{:,.0f}',
        'publico_total': '{:,.0f}',
        'receita_bruta_total': 'R$ {:,.2f}',
        'despesa_total': 'R$ {:,.2f}',
        'resultado_liquido': 'R$ {:,.2f}',
        'ticket_medio': 'R$ {:,.2f}',
        'margem_liquida': '{:.2%}'
    }
    
    # Filter formatters for columns that exist in data_display
    active_formatters = {k: v for k, v in formatters.items() if k in data_display.columns}

    for col, fmt in active_formatters.items():
        if col in data_display.columns:
            if isinstance(fmt, str) and ('f' in fmt or '%' in fmt) and col != 'data_jogo': 
                 data_display[col] = pd.to_numeric(data_display[col], errors='coerce')

    try:
        if not data_display.empty:
            st.dataframe(data_display.style.format(active_formatters, na_rep='-'), use_container_width=True)
        else:
            st.info("Nenhum dado bruto para exibir com os filtros atuais.")
    except Exception as e:
        st.error(f"Erro ao formatar a tabela de dados brutos: {e}")
        if not data_display.empty:
            st.dataframe(data_display, use_container_width=True) # Fallback
        else:
            st.info("Nenhum dado bruto para exibir com os filtros atuais (fallback).")
