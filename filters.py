import streamlit as st
import pandas as pd
import datetime

def render_sidebar_filters(df):
    st.sidebar.title("🔍 Filtros do Painel")

    # Garante conversão correta da coluna de datas
    datas_series = pd.to_datetime(df["Data da tarefa"], errors="coerce").dt.date
    datas_validas = datas_series.dropna()

    # Define limites padrão resilientes
    if not datas_validas.empty:
        min_date = datas_validas.min()
        max_date = datas_validas.max()
    else:
        min_date = datetime.date(2026, 1, 1)
        max_date = datetime.date(2026, 12, 31)

    date_range = st.sidebar.date_input(
        "Período (Obrigatório)*",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Filtros Auxiliares
    tipo = st.sidebar.selectbox("Tipo de Tarefa", ["Todas", "Preventiva", "Corretiva"])
    maquina = st.sidebar.multiselect("Máquina", options=sorted(df["Máquina"].dropna().astype(str).unique()))
    tecnico = st.sidebar.multiselect("Técnico", options=sorted(df["Técnico"].dropna().astype(str).unique()))
    cliente = st.sidebar.multiselect("Cliente", options=sorted(df["Cliente"].dropna().astype(str).unique()))
    cidade = st.sidebar.multiselect("Cidade", options=sorted(df["Cidade"].dropna().astype(str).unique()))
    regiao = st.sidebar.multiselect("Região", options=sorted(df["Região"].dropna().astype(str).unique()))
    estado = st.sidebar.multiselect("Estado", options=sorted(df["Estado"].dropna().astype(str).unique()))

    if st.sidebar.button("🧹 Limpar Filtros"):
        st.session_state.clear()
        st.rerun()

    is_date_valid = isinstance(date_range, (tuple, list)) and len(date_range) == 2
    has_additional_filter = any([
        tipo != "Todas", len(maquina) > 0, len(tecnico) > 0,
        len(cliente) > 0, len(cidade) > 0, len(regiao) > 0, len(estado) > 0
    ])

    df_filtered = df.copy()

    # Aplicar Filtro de Datas com comparação direta de objetos datetime.date
    if is_date_valid:
        start, end = date_range
        # Extrai os objetos date com segurança para a filtragem
        df_dates = pd.to_datetime(df_filtered["Data da tarefa"], errors="coerce").dt.date
        mask_date = (df_dates >= start) & (df_dates <= end)
        df_filtered = df_filtered[mask_date]

    # Filtros por categorias
    if tipo != "Todas":
        df_filtered = df_filtered[df_filtered["Tipo"] == tipo]
    if maquina:
        df_filtered = df_filtered[df_filtered["Máquina"].isin(maquina)]
    if tecnico:
        df_filtered = df_filtered[df_filtered["Técnico"].isin(tecnico)]
    if cliente:
        df_filtered = df_filtered[df_filtered["Cliente"].isin(cliente)]
    if cidade:
        df_filtered = df_filtered[df_filtered["Cidade"].isin(cidade)]
    if regiao:
        df_filtered = df_filtered[df_filtered["Região"].isin(regiao)]
    if estado:
        df_filtered = df_filtered[df_filtered["Estado"].isin(estado)]

    return df_filtered, is_date_valid, has_additional_filter
