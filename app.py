import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_and_normalize_data
from filters import render_sidebar_filters

# 1. Configuração da página
st.set_page_config(
    page_title="Painel Executivo de Manutenção",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Estilização CSS voltada APENAS para os Cards do Topo (Primeira Parte)
st.markdown("""
    <style>
        /* Estilo dos Cards Executivos do Topo */
        .exec-card {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 18px 20px;
            border-left: 5px solid #0284c7;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            margin-bottom: 15px;
        }
        .exec-card-green { border-left-color: #16a34a; }
        .exec-card-amber { border-left-color: #d97706; }
        .exec-card-red   { border-left-color: #dc2626; }
        
        .exec-title {
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .exec-value {
            font-size: 28px;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.1;
        }
        .exec-sub {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 4px;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Carregamento dos dados
df_raw = load_and_normalize_data()

if df_raw.empty:
    st.warning("Nenhum dado encontrado para exibição.")
    st.stop()

# 4. Renderização dos Filtros na Barra Lateral
df_filtered, is_date_valid, has_additional_filter = render_sidebar_filters(df_raw)

# --- PRIMEIRA PARTE: CABEÇALHO E CARDS EXECUTIVOS DO TOPO ---

st.title("📊 Painel Executivo de Manutenção & Ativos")
st.caption("Visão consolidada e estratégica dos indicadores de atendimento")

# Cálculo dos Indicadores do Topo
total_chamados = len(df_filtered)

if "Tipo" in df_filtered.columns:
    preventivas = len(df_filtered[df_filtered["Tipo"].astype(str).str.contains("Preventiva", case=False, na=False)])
    corretivas = len(df_filtered[df_filtered["Tipo"].astype(str).str.contains("Corretiva", case=False, na=False)])
else:
    preventivas = 0
    corretivas = 0

garantia_cnt = len(df_filtered[df_filtered["Garantia"] == "Dentro"]) if "Garantia" in df_filtered.columns else 0
pct_garantia = (garantia_cnt / total_chamados * 100) if total_chamados > 0 else 0

# Renderização dos Cards Executivos em 4 Colunas
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
        <div class="exec-card">
            <div class="exec-title">Total de Atendimentos</div>
            <div class="exec-value">{total_chamados}</div>
            <div class="exec-sub">Registros no período</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="exec-card exec-card-green">
            <div class="exec-title">Preventivas</div>
            <div class="exec-value">{preventivas}</div>
            <div class="exec-sub">Manutenções programadas</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="exec-card exec-card-amber">
            <div class="exec-title">Corretivas</div>
            <div class="exec-value">{corretivas}</div>
            <div class="exec-sub">Atendimentos de reparo</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
        <div class="exec-card exec-card-red">
            <div class="exec-title">Em Garantia</div>
            <div class="exec-value">{pct_garantia:.1f}%</div>
            <div class="exec-sub">{garantia_cnt} equipamento(s) cobertos</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- SEGUNDA PARTE: RESTANTE DO APLICATIVO (GRÁFICOS E TABELA) ---

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Manutenções por Tipo")
    if "Tipo" in df_filtered.columns and not df_filtered.empty:
        df_tipo = df_filtered["Tipo"].value_counts().reset_index()
        df_tipo.columns = ["Tipo", "Quantidade"]
        fig_tipo = px.pie(
            df_tipo, 
            names="Tipo", 
            values="Quantidade", 
            hole=0.4,
            color_discrete_sequence=["#0284c7", "#f59e0b", "#16a34a", "#dc2626"]
        )
        st.plotly_chart(fig_tipo, use_container_width=True)

with col_g2:
    st.subheader("Top 5 Problemas Relatados")
    if "Problema" in df_filtered.columns and not df_filtered.empty:
        df_prob = df_filtered["Problema"].value_counts().head(5).reset_index()
        df_prob.columns = ["Problema", "Quantidade"]
        fig_prob = px.bar(
            df_prob, 
            x="Quantidade", 
            y="Problema", 
            orientation="h",
            color_discrete_sequence=["#0284c7"]
        )
        fig_prob.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_prob, use_container_width=True)

st.subheader("Atendimentos por Técnico")
if "Técnico" in df_filtered.columns and not df_filtered.empty:
    df_tech = df_filtered["Técnico"].value_counts().reset_index()
    df_tech.columns = ["Técnico", "Atendimentos"]
    fig_tech = px.bar(
        df_tech, 
        x="Técnico", 
        y="Atendimentos",
        color_discrete_sequence=["#0f172a"]
    )
    st.plotly_chart(fig_tech, use_container_width=True)

st.subheader("Detalhamento dos Registros")
st.dataframe(df_filtered, use_container_width=True, hide_index=True)
