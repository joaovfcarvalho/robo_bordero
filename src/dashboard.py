import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide") # Moved to the top

# Load data
@st.cache_data
def load_data():
    data = pd.read_csv("csv/jogos_resumo_clean.csv") # Removed parse_dates from here
    
    # Explicitly convert 'data_jogo' to datetime, coercing errors to NaT
    data['data_jogo'] = pd.to_datetime(data['data_jogo'], errors='coerce')

    # Ensure relevant columns are numeric, coercing errors to NaN
    numeric_cols = ['receita_bruta_total', 'publico_total', 'resultado_liquido']
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    # Calculate additional metrics
    data['ticket_medio'] = data['receita_bruta_total'] / data['publico_total']
    data['margem_liquida'] = data['resultado_liquido'] / data['receita_bruta_total']
    
    # Replace inf values with NaN, then fill NaN with 0 (or an appropriate value)
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    data['ticket_medio'].fillna(0, inplace=True)
    data['margem_liquida'].fillna(0, inplace=True)
    
    # Create Portuguese day of the week
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
    
    return data

data = load_data()

st.title("CBF Robot - Análise de Jogos de Futebol")

# --- FILTERS ---
st.sidebar.header("Filtros")

# Date range filter
min_date = data['data_jogo'].min()
max_date = data['data_jogo'].max()

if pd.isna(min_date) or pd.isna(max_date):
    st.sidebar.warning("Datas de jogos não disponíveis para criar o filtro de período.")
    # Set default dates if min_date or max_date is NaT
    # This might happen if the 'data_jogo' column is all NaT after pd.to_datetime
    from datetime import datetime
    min_date = datetime(2020, 1, 1)
    max_date = datetime.now()
    selected_date_range = (min_date, max_date) # Default to a wide range
else:
    # Ensure min_date and max_date are Timestamps for the slider
    min_date_ts = pd.Timestamp(min_date)
    max_date_ts = pd.Timestamp(max_date)
    
    # Default to the last available year or the full range if only one year
    default_start_date = max_date_ts.replace(month=1, day=1) if max_date_ts.year > min_date_ts.year else min_date_ts
    default_end_date = max_date_ts

    selected_date_range = st.sidebar.slider(
        "Período do Jogo",
        min_value=min_date_ts.to_pydatetime(), # Convert to python datetime
        max_value=max_date_ts.to_pydatetime(), # Convert to python datetime
        value=(default_start_date.to_pydatetime(), default_end_date.to_pydatetime()), # Convert to python datetime
        format="DD/MM/YYYY"
    )

# Filter data by selected date range first
# Convert selected_date_range to Timestamp for comparison
start_date_filter = pd.Timestamp(selected_date_range[0])
end_date_filter = pd.Timestamp(selected_date_range[1])

data_filtrada_periodo = data[
    (data['data_jogo'] >= start_date_filter) & (data['data_jogo'] <= end_date_filter)
].copy()


competicao = st.sidebar.multiselect(
    "Competição",
    options=data_filtrada_periodo["competicao"].dropna().unique(),
    default=data_filtrada_periodo["competicao"].dropna().unique()
)

times_mandantes_options = sorted(data_filtrada_periodo["time_mandante"].dropna().unique())
time_mandante_selecionado = st.sidebar.multiselect(
    "Time Mandante",
    options=times_mandantes_options,
    default=times_mandantes_options
)

times_visitantes_options = sorted(data_filtrada_periodo["time_visitante"].dropna().unique())
time_visitante_selecionado = st.sidebar.multiselect(
    "Time Visitante",
    options=times_visitantes_options,
    default=times_visitantes_options
)

# Apply filters
data_dashboard = data_filtrada_periodo[
    data_filtrada_periodo["competicao"].isin(competicao) &
    data_filtrada_periodo["time_mandante"].isin(time_mandante_selecionado) &
    data_filtrada_periodo["time_visitante"].isin(time_visitante_selecionado)
].copy() # Use .copy() to avoid SettingWithCopyWarning

if data_dashboard.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    # --- GENERAL STATS ---
    st.header("Estatísticas Gerais do Período Filtrado")
    total_jogos = data_dashboard.shape[0]
    total_publico = data_dashboard['publico_total'].sum()
    total_receita = data_dashboard['receita_bruta_total'].sum()
    # Calculate overall ticket_medio and margem_liquida carefully to avoid division by zero
    overall_ticket_medio = total_receita / total_publico if total_publico > 0 else 0
    overall_margem_liquida = data_dashboard['resultado_liquido'].sum() / total_receita if total_receita > 0 else 0
    total_receita_milhoes = total_receita / 1_000_000


    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total de Jogos", f"{total_jogos:,}")
    col2.metric("Público Total", f"{total_publico:,.0f}")
    col3.metric("Receita Bruta Total", f"R$ {total_receita_milhoes:,.2f}M")
    col4.metric("Ticket Médio Geral", f"R$ {overall_ticket_medio:,.2f}")
    col5.metric("Margem Líquida Média", f"{overall_margem_liquida:.2%}")

    st.markdown("---")

    # --- ATTENDANCE ANALYSIS ---
    st.header("Análise de Público")
    col1_publico, col2_publico = st.columns(2)

    with col1_publico:
        st.subheader("Público Médio por Dia da Semana")
        # Group by Portuguese day name, calculate mean, then sort by the categorical order (day of week)
        # or by value. Let's sort by value (mean attendance) for now.
        dia_semana_publico = data_dashboard.groupby('dia_semana_pt', observed=False)['publico_total'].mean().sort_values(ascending=False)
        st.bar_chart(dia_semana_publico)
        st.caption("Mostra o público médio para cada dia da semana em que ocorreram jogos.")

    with col2_publico:
        st.subheader("Distribuição do Público Total")
        # Drop NaN values before creating histogram to avoid errors
        publico_total_valid = data_dashboard['publico_total'].dropna()
        if not publico_total_valid.empty:
            # Create bins for the histogram
            try:
                bins = pd.cut(publico_total_valid, bins=10) # Use 10 bins for better readability
                publico_dist = publico_total_valid.groupby(bins, observed=False).size()
                publico_dist.index = publico_dist.index.astype(str) # Convert IntervalIndex to string for display
                st.bar_chart(publico_dist)
                st.caption("Histograma mostrando a frequência de diferentes faixas de público total.")
            except Exception as e:
                st.info(f"Não foi possível gerar o histograma de público: {e}")
        else:
            st.info("Não há dados de público suficientes para gerar o histograma.")


    col3_publico, col4_publico = st.columns(2)
    with col3_publico:
        st.subheader("Público Médio por Time Mandante")
        publico_medio_mandante = data_dashboard.groupby('time_mandante')['publico_total'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(publico_medio_mandante)
        st.caption("Top 20 times com maior público médio quando mandantes.")

    with col4_publico:
        st.subheader("Público Médio por Time Visitante")
        publico_medio_visitante = data_dashboard.groupby('time_visitante')['publico_total'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(publico_medio_visitante)
        st.caption("Top 20 times com maior público médio quando visitantes.")
    
    st.markdown("---")

    # --- FINANCIAL ANALYSIS ---
    st.header("Análise Financeira")
    col1_fin, col2_fin = st.columns(2)

    with col1_fin:
        st.subheader("Ticket Médio por Clube (Mandante)")
        ticket_medio_clube = data_dashboard.groupby('time_mandante')['ticket_medio'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(ticket_medio_clube)
        st.caption("Top 20 times com maior ticket médio quando mandantes.")

    with col2_fin:
        st.subheader("Margem Líquida Média por Clube (Mandante)")
        margem_liquida_clube = data_dashboard.groupby('time_mandante')['margem_liquida'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(margem_liquida_clube)
        st.caption("Top 20 times com maior margem líquida média quando mandantes. Valores podem ser negativos.")

    st.subheader("Relação Público Total vs. Ticket Médio")
    # Ensure no NaN values in columns for scatter plot
    scatter_data = data_dashboard[['publico_total', 'ticket_medio']].dropna()
    if not scatter_data.empty:
        st.scatter_chart(scatter_data, x='publico_total', y='ticket_medio', size='publico_total')
        st.caption("Cada ponto representa um jogo. O tamanho do ponto pode indicar o público (opcional).")
    else:
        st.info("Não há dados suficientes para o gráfico de dispersão.")

    st.markdown("---")
    
    # --- TOP 5 GAMES ---
    st.header("Top 5 Jogos")
    col1_top, col2_top = st.columns(2)
    col3_top, col4_top = st.columns(2)

    with col1_top:
        st.subheader("Por Maior Público Total")
        top_publico = data_dashboard.nlargest(5, 'publico_total')[['data_jogo', 'time_mandante', 'time_visitante', 'publico_total', 'competicao']]
        top_publico_display = top_publico.copy()
        top_publico_display['data_jogo'] = top_publico_display['data_jogo'].dt.strftime('%d/%m/%y')
        st.dataframe(top_publico_display.style.format({"publico_total": "{:,.0f}"}))
    
    with col2_top:
        st.subheader("Por Maior Receita Bruta")
        top_receita = data_dashboard.nlargest(5, 'receita_bruta_total')[['data_jogo', 'time_mandante', 'time_visitante', 'receita_bruta_total', 'competicao']]
        top_receita_display = top_receita.copy()
        top_receita_display['data_jogo'] = top_receita_display['data_jogo'].dt.strftime('%d/%m/%y')
        st.dataframe(top_receita_display.style.format({"receita_bruta_total": "R$ {:,.2f}".replace('_', '.')}))

    with col3_top:
        st.subheader("Por Maior Ticket Médio")
        # Filter out games with zero public to avoid misleading high ticket_medio from zero division
        top_ticket = data_dashboard[data_dashboard['publico_total'] > 0].nlargest(5, 'ticket_medio')[['data_jogo', 'time_mandante', 'time_visitante', 'ticket_medio', 'publico_total', 'competicao']]
        top_ticket_display = top_ticket.copy()
        top_ticket_display['data_jogo'] = top_ticket_display['data_jogo'].dt.strftime('%d/%m/%y')
        st.dataframe(top_ticket_display.style.format({"ticket_medio": "R$ {:_.2f}".replace('_', '.'), "publico_total": "{:_.0f}".replace('_', '.')}))

    with col4_top:
        st.subheader("Por Maior Margem Líquida")
        # Filter out games with zero revenue to avoid misleading high margem_liquida from zero division
        top_margem = data_dashboard[data_dashboard['receita_bruta_total'] != 0].nlargest(5, 'margem_liquida')[['data_jogo', 'time_mandante', 'time_visitante', 'margem_liquida', 'receita_bruta_total', 'competicao']]
        top_margem_display = top_margem.copy()
        top_margem_display['data_jogo'] = top_margem_display['data_jogo'].dt.strftime('%d/%m/%y')
        st.dataframe(top_margem_display.style.format({"margem_liquida": "{:.2%}", "receita_bruta_total": "R$ {:_.2f}".replace('_', '.')}))

    st.markdown("---")

    # Display raw data
    st.header("Dados Brutos Filtrados")
    st.write(f"Exibindo {data_dashboard.shape[0]} jogos.")
    
    # Prepare data for display, handling NaT in 'data_jogo' for formatting
    data_display = data_dashboard.drop(columns=['dia_semana_en']).copy()
    
    # Formatters - using lambda for date to handle NaT
    formatters = {
        'data_jogo': lambda x: x.strftime('%d/%m/%y') if pd.notnull(x) else '',
        'publico_pagante': '{:_.0f}'.replace('_', '.'),
        'publico_nao_pagante': '{:_.0f}'.replace('_', '.'),
        'publico_total': '{:_.0f}'.replace('_', '.'),
        'receita_bruta_total': 'R$ {:_.2f}'.replace('_', '.'),
        'despesa_total': 'R$ {:_.2f}'.replace('_', '.'),
        'resultado_liquido': 'R$ {:_.2f}'.replace('_', '.'),
        'ticket_medio': 'R$ {:_.2f}'.replace('_', '.'),
        'margem_liquida': '{:.2%}'
    }
    
    # Apply formatting. Using st.dataframe without .style if direct formatting is problematic,
    # or ensure all columns in formatters exist and types are compatible.
    # Forcing numeric columns to be float before applying float formatters can help.
    for col, fmt in formatters.items():
        if col in data_display.columns:
            if isinstance(fmt, str) and ('f' in fmt or '%' in fmt) and col != 'data_jogo': # Numeric formats
                 data_display[col] = pd.to_numeric(data_display[col], errors='coerce') # Ensure numeric
            # For date, it's handled by lambda. For others, style.format will apply.

    try:
        st.dataframe(data_display.style.format(formatters, na_rep='-'))
    except Exception as e:
        st.error(f"Erro ao formatar a tabela de dados brutos: {e}")
        st.dataframe(data_display) # Fallback to unformatted display
