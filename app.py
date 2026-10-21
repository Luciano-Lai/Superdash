import sys
import os

# ==============================================================================
# 1. RESOLUÇÃO DE CAMINHOS DO PYTHON (PASTA VIEWS)
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR in sys.path:
    sys.path.remove(BASE_DIR)
sys.path.insert(0, BASE_DIR)

VIEWS_DIR = os.path.join(BASE_DIR, "views")
if VIEWS_DIR not in sys.path:
    sys.path.append(VIEWS_DIR)

# ==============================================================================
# 2. IMPORTAÇÃO DOS PACOTES E MÓDULOS NATIVOS
# ==============================================================================
import streamlit as st
import pandas as pd

# Módulos base localizados na raiz do projeto
from data_loader import load_and_normalize_data
from filters import render_sidebar_filters
from kpis import calculate_executive_kpis

# Importação direta dos scripts da pasta views/
import views.monitoramento as v_mon
import views.maquinas as v_maq
import views.corretivas as v_corr
import views.clientes_regioes as v_cli
import views.analise_tarefas as v_tar

# ==============================================================================
# 3. CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="SuperDash - Monitoramento Executivo",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 4. ESTILIZAÇÃO C-LEVEL (NAVY/SLATE, KPI CARDS & ABAS)
# ==============================================================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        .main {
            background-color: #F8FAFC;
        }
        #MainMenu, footer, header { visibility: hidden; }
        
        /* Cabeçalho Executivo Navy/Slate */
        .exec-header-container {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            padding: 22px 28px;
            border-radius: 14px;
            color: #FFFFFF;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.12);
        }
        .exec-header-title {
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin: 0;
            color: #FFFFFF;
        }
        .exec-header-subtitle {
            font-size: 13px;
            color: #94A3B8;
            margin-top: 4px;
        }
        
        /* Cartões de KPI Estilizados */
        .kpi-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 18px 22px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
            margin-bottom: 12px;
        }
        .kpi-border-primary { border-left: 5px solid #0284C7; }
        .kpi-border-success { border-left: 5px solid #16A34A; }
        .kpi-border-warning { border-left: 5px solid #F59E0B; }
        .kpi-border-danger  { border-left: 5px solid #DC2626; }
        
        .kpi-label {
            font-size: 11px;
            font-weight: 700;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 30px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1;
        }
        .kpi-footer {
            font-size: 11px;
            color: #64748B;
            margin-top: 6px;
        }

        /* Abas de Navegação Fluida */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #E2E8F0;
            padding: 6px;
            border-radius: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #0284C7 !important;
            font-weight: 700;
            box-shadow: 0 2px 4px rgba(0,0,0,0.06);
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. CARREGAMENTO DOS DADOS & FILTROS GLOBAIS
# ==============================================================================
df_raw = load_and_normalize_data()

if df_raw.empty:
    st.error("⚠️ Não foi possível carregar os dados. Verifique a conexão com a planilha.")
    st.stop()

filter_output = render_sidebar_filters(df_raw)
df_filtered = filter_output[0] if isinstance(filter_output, tuple) else filter_output

# ==============================================================================
# 6. TOPO EXECUTIVO (HEADER & KPI CARDS)
# ==============================================================================
st.markdown("""
    <div class="exec-header-container">
        <div class="exec-header-title">❄️ SuperDash - Monitoramento Executivo de Refrigeração</div>
        <div class="exec-header-subtitle">Painel Integrado de Gestão de Ativos, Inteligência Operacional e Cobertura de Garantias</div>
    </div>
""", unsafe_allow_html=True)

kpis = calculate_executive_kpis(df_filtered)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
        <div class="kpi-card kpi-border-primary">
            <div class="kpi-label">Total de Atendimentos</div>
            <div class="kpi-value">{kpis['total_chamados']:,}</div>
            <div class="kpi-footer">📋 Registros no período</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="kpi-card kpi-border-success">
            <div class="kpi-label">Preventivas</div>
            <div class="kpi-value">{kpis['preventivas']:,}</div>
            <div class="kpi-footer">🟢 {kpis['pct_preventivas']:.1f}% de eficiência</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="kpi-card kpi-border-warning">
            <div class="kpi-label">Corretivas</div>
            <div class="kpi-value">{kpis['corretivas']:,}</div>
            <div class="kpi-footer">🟠 Reparos e emergências</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    variant_gar = "kpi-border-success" if kpis['pct_garantia'] >= 30 else "kpi-border-danger"
    st.markdown(f"""
        <div class="kpi-card {variant_gar}">
            <div class="kpi-label">Em Garantia</div>
            <div class="kpi-value">{kpis['pct_garantia']:.1f}%</div>
            <div class="kpi-footer">🛡️ {kpis['garantia_qtd']} ativo(s) cobertos</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# Helper para executar as funções de renderização nativas da pasta views/
def call_view_render(mod, df):
    for attr in dir(mod):
        if attr.startswith("render") or attr == "main":
            func = getattr(mod, attr)
            if callable(func):
                try:
                    func(df)
                    return
                except TypeError:
                    func()
                    return

# ==============================================================================
# 7. NAVEGAÇÃO EXECUTIVA POR ABAS FLUIDAS
# ==============================================================================
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📊 Monitoramento Geral", 
    "⚙️ Máquinas & Comparativos", 
    "🚨 Manutenções Corretivas", 
    "🏢 Clientes & Regiões", 
    "📝 Análise de Tarefas",
    "📋 Tabela Operacional"
])

with t1:
    call_view_render(v_mon, df_filtered)

with t2:
    call_view_render(v_maq, df_filtered)

with t3:
    call_view_render(v_corr, df_filtered)

with t4:
    call_view_render(v_cli, df_filtered)

with t5:
    call_view_render(v_tar, df_filtered)

with t6:
    st.subheader("Base Operacional Completa")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
