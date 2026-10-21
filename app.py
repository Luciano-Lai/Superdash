import streamlit as st
import pandas as pd
import plotly.express as px

from data_loader import load_and_normalize_data
from filters import render_sidebar_filters
from kpis import calculate_executive_kpis
from ui import apply_executive_ui, render_executive_header, render_kpi_card

# 1. Aplicar estilo global executivo
apply_executive_ui()

# 2. Carregamento resiliente dos dados
df_raw = load_and_normalize_data()

if df_raw.empty:
    st.error("⚠️ Não foi possível carregar os dados da planilha. Verifique a conexão com o Google Sheets.")
    st.stop()

# 3. Filtros na Barra Lateral
df_filtered, is_date_valid, has_additional_filter = render_sidebar_filters(df_raw)

# 4. Cabeçalho Executivo Principal
render_executive_header(
    title="🏢 Executive Operations Dashboard",
    subtitle="Visão consolidada do parque de refrigeração, eficiência de manutenção e cobertura de garantias"
)

# 5. Cálculo dos KPIs Globais
kpis = calculate_executive_kpis(df_filtered)

# 6. Grid de Cards de KPI Executivos (Top-Level)
c1, c2, c3, c4 = st.columns(4)

with c1:
    render_kpi_card(
        title="Volume de Atendimentos",
        value=f"{kpis['total_chamados']:,}",
        footer="📋 Registros no período selecionado",
        variant="primary"
    )

with c2:
    render_kpi_card(
        title="Manutenções Preventivas",
        value=f"{kpis['preventivas']:,}",
        footer=f"🟢 {kpis['pct_preventivas']:.1f}% do total de operações",
        variant="success"
    )

with c3:
    render_kpi_card(
        title="Atendimentos Corretivos",
        value=f"{kpis['corretivas']:,}",
        footer="🟠 Intervenções de reparo imediato",
        variant="warning"
    )

with c4:
    render_kpi_card(
        title="Equipamentos em Garantia",
        value=f"{kpis['pct_garantia']:.1f}%",
        footer=f"🛡️ {kpis['garantia_qtd']} ativo(s) protegidos",
        variant="danger" if kpis['pct_garantia'] < 30 else "success"
    )

st.write("")
st.write("")

# 7. NAVEGAÇÃO EXECUTIVA POR ABAS (Tabs)
tab1, tab2, tab3 = st.tabs([
    "📈 Visão Estratégica & Performance", 
    "🛠️ Análise Técnica de Ativos", 
    "📑 Relatório Operacional & Exportação"
])

# --- ABA 1: VISÃO ESTRATÉGICA & PERFORMANCE ---
with tab1:
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Proporção: Preventivas vs. Corretivas")
        if "Tipo" in df_filtered.columns and not df_filtered.empty:
            df_tipo = df_filtered["Tipo"].value_counts().reset_index()
            df_tipo.columns = ["Tipo", "Quantidade"]
            fig_pie = px.pie(
                df_tipo, 
                names="Tipo", 
                values="Quantidade", 
                hole=0.5,
                color_discrete_sequence=["#0284C7", "#F59E0B", "#16A34A", "#DC2626"]
            )
            fig_pie.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                height=340,
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.subheader("Top 5 Incidências de Falhas / Problemas")
        if "Problema" in df_filtered.columns and not df_filtered.empty:
            df_prob = df_filtered["Problema"].value_counts().head(5).reset_index()
            df_prob.columns = ["Problema", "Quantidade"]
            fig_bar = px.bar(
                df_prob, 
                x="Quantidade", 
                y="Problema", 
                orientation="h",
                color_discrete_sequence=["#0284C7"]
            )
            fig_bar.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=20, b=20, l=20, r=20),
                height=340
            )
            st.plotly_chart(fig_bar, use_container_width=True)

# --- ABA 2: ANÁLISE TÉCNICA DE ATIVOS ---
with tab2:
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.subheader("Volume de Atendimentos por Técnico")
        if "Técnico" in df_filtered.columns and not df_filtered.empty:
            df_tech = df_filtered["Técnico"].value_counts().reset_index()
            df_tech.columns = ["Técnico", "Atendimentos"]
            fig_tech = px.bar(
                df_tech, 
                x="Técnico", 
                y="Atendimentos",
                color_discrete_sequence=["#0F172A"]
            )
            fig_tech.update_layout(height=340, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_tech, use_container_width=True)

    with col_t2:
        st.subheader("Status de Garantia por Equipamento")
        if "Garantia" in df_filtered.columns and not df_filtered.empty:
            df_gar = df_filtered["Garantia"].value_counts().reset_index()
            df_gar.columns = ["Status", "Quantidade"]
            fig_gar = px.bar(
                df_gar, 
                x="Status", 
                y="Quantidade",
                color="Status",
                color_discrete_map={"Dentro": "#16A34A", "Fora": "#DC2626", "Não informado": "#94A3B8"}
            )
            fig_gar.update_layout(height=340, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_gar, use_container_width=True)

# --- ABA 3: RELATÓRIO OPERACIONAL & EXPORTAÇÃO ---
with tab3:
    st.subheader("Base Operacional Consolidada")
    st.caption("Visão analítica dos registros filtrados para auditoria e controle de ativos.")
    
    st.dataframe(
        df_filtered, 
        use_container_width=True, 
        hide_index=True
    )