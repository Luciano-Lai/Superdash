import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_and_normalize_data

# 1. Configuração da página e tema executivo
st.set_page_config(
    page_title="Painel Executivo de Manutenção",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Injeção de CSS customizado para acabamento profissional
st.markdown("""
    <style>
        /* Estilo do fundo principal */
        .main {
            background-color: #f8fafc;
        }
        
        /* Ocultar marca e menu padrão do Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Formatação dos Cards de KPI Executivos */
        .kpi-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 20px 24px;
            border-left: 5px solid #0284c7;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            margin-bottom: 12px;
        }
        .kpi-card-success { border-left-color: #16a34a; }
        .kpi-card-warning { border-left-color: #f59e0b; }
        .kpi-card-danger { border-left-color: #dc2626; }
        
        .kpi-title {
            font-size: 13px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 32px;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.1;
        }
        .kpi-sub {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 6px;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Carregamento dos dados via data_loader
df_raw = load_and_normalize_data()

if df_raw.empty:
    st.warning("Nenhum dado encontrado para exibição.")
    st.stop()

# 4. Filtros na Barra Lateral (Sidebar)
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=60)
st.sidebar.title("Filtros Estratégicos")

# Filtro por Cliente
clientes_opt = ["Todos"] + sorted([str(x) for x in df_raw["Cliente"].unique() if x != "Não especificado"])
cliente_sel = st.sidebar.selectbox("Cliente", clientes_opt)

# Filtro por Tipo de Manutenção
tipos_opt = ["Todos"] + sorted([str(x) for x in df_raw["Tipo"].unique() if x != "Não especificado"])
tipo_sel = st.sidebar.selectbox("Tipo de Manutenção", tipos_opt)

# Filtro por Técnico
tecnicos_opt = ["Todos"] + sorted([str(x) for x in df_raw["Técnico"].unique() if x != "Não especificado"])
tecnico_sel = st.sidebar.selectbox("Técnico Responsável", tecnicos_opt)

# Aplicação dos Filtros
df = df_raw.copy()
if cliente_sel != "Todos":
    df = df[df["Cliente"] == cliente_sel]
if tipo_sel != "Todos":
    df = df[df["Tipo"] == tipo_sel]
if tecnico_sel != "Todos":
    df = df[df["Técnico"] == tecnico_sel]

# 5. Cabeçalho Executivo
st.title("📊 Painel Executivo de Manutenção & Ativos")
st.caption("Visão estratégica em tempo real dos chamados, garantias e parque de equipamentos.")

st.markdown("---")

# 6. Mapeamento dos Cards de KPI Superiores
total_chamados = len(df)
preventivas = len(df[df["Tipo"].str.contains("Preventiva", case=False, na=False)])
corretivas = len(df[df["Tipo"].str.contains("Corretiva", case=False, na=False)])
dentro_garantia = len(df[df["Garantia"] == "Dentro"]) if "Garantia" in df.columns else 0

pct_garantia = (dentro_garantia / total_chamados * 100) if total_chamados > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total de Chamados</div>
            <div class="kpi-value">{total_chamados}</div>
            <div class="kpi-sub">Registros no período</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="kpi-card kpi-card-success">
            <div class="kpi-title">Preventivas</div>
            <div class="kpi-value">{preventivas}</div>
            <div class="kpi-sub">Manutenções planejadas</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="kpi-card kpi-card-warning">
            <div class="kpi-title">Corretivas</div>
            <div class="kpi-value">{corretivas}</div>
            <div class="kpi-sub">Reparos de emergência</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="kpi-card kpi-card-danger">
            <div class="kpi-title">Em Garantia</div>
            <div class="kpi-value">{pct_garantia:.1f}%</div>
            <div class="kpi-sub">{dentro_garantia} equipamento(s) cobertos</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# 7. Organização em Abas Estratégicas
tab_dashboard, tab_tecnica, tab_tabela = st.tabs(["📈 Visão Executiva", "🛠️ Análise Técnica", "📋 Relatório Operacional"])

with tab_dashboard:
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Distribuição por Tipo de Manutenção")
        if "Tipo" in df.columns and not df.empty:
            df_tipo = df["Tipo"].value_counts().reset_index()
            df_tipo.columns = ["Tipo", "Qtd"]
            fig_tipo = px.pie(
                df_tipo, 
                names="Tipo", 
                values="Qtd", 
                hole=0.5,
                color_discrete_sequence=["#0284c7", "#f59e0b", "#16a34a", "#dc2626"]
            )
            fig_tipo.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320)
            st.plotly_chart(fig_tipo, use_container_width=True)

    with col_chart2:
        st.subheader("Top 5 Falhas / Problemas Relatados")
        if "Problema" in df.columns and not df.empty:
            df_prob = df["Problema"].value_counts().head(5).reset_index()
            df_prob.columns = ["Problema", "Qtd"]
            fig_prob = px.bar(
                df_prob, 
                x="Qtd", 
                y="Problema", 
                orientation="h",
                color_discrete_sequence=["#0284c7"]
            )
            fig_prob.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=20, b=20, l=20, r=20),
                height=320
            )
            st.plotly_chart(fig_prob, use_container_width=True)

with tab_tecnica:
    col_tech1, col_tech2 = st.columns(2)
    
    with col_tech1:
        st.subheader("Atendimentos por Técnico")
        if "Técnico" in df.columns and not df.empty:
            df_tech = df["Técnico"].value_counts().reset_index()
            df_tech.columns = ["Técnico", "Atendimentos"]
            fig_tech = px.bar(
                df_tech, 
                x="Técnico", 
                y="Atendimentos",
                color_discrete_sequence=["#0f172a"]
            )
            fig_tech.update_layout(height=320, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_tech, use_container_width=True)

    with col_tech2:
        st.subheader("Status de Garantia dos Ativos")
        if "Garantia" in df.columns and not df.empty:
            df_gar = df["Garantia"].value_counts().reset_index()
            df_gar.columns = ["Status", "Qtd"]
            fig_gar = px.bar(
                df_gar, 
                x="Status", 
                y="Qtd",
                color="Status",
                color_discrete_map={"Dentro": "#16a34a", "Fora": "#dc2626", "Não informado": "#94a3b8"}
            )
            fig_gar.update_layout(height=320, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_gar, use_container_width=True)

with tab_tabela:
    st.subheader("Tabela de Registros Filtrados")
    st.dataframe(df, use_container_width=True, hide_index=True)
