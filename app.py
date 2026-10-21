import sys
import os
import importlib.util
import streamlit as st
import pandas as pd

# 1. Ajuste dinâmico de caminhos do Python para encontrar a pasta 'view' e módulos raiz
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

VIEW_DIR = os.path.join(BASE_DIR, "view")
if os.path.exists(VIEW_DIR) and VIEW_DIR not in sys.path:
    sys.path.insert(0, VIEW_DIR)

# Importações dos módulos nativos do SuperDash
from data_loader import load_and_normalize_data
from filters import render_sidebar_filters
from kpis import calculate_executive_kpis

# Função de carregamento dinâmico e seguro para os arquivos da pasta view
def load_view_module(module_name):
    try:
        # Tenta importar como pacote
        return importlib.import_module(f"view.{module_name}")
    except (ModuleNotFoundError, ImportError):
        try:
            # Tenta importar diretamente da raiz/sys.path
            return importlib.import_module(module_name)
        except (ModuleNotFoundError, ImportError):
            # Tenta carregar explicitamente pelo caminho do arquivo no disco
            file_path = os.path.join(VIEW_DIR, f"{module_name}.py")
            if os.path.exists(file_path):
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
            return None

# Carregamento resiliente de cada visão
v_mon = load_view_module("monitoramento")
v_maq = load_view_module("maquinas")
v_corr = load_view_module("corretivas")
v_cli = load_view_module("clientes_regioes")
v_tar = load_view_module("analise_tarefas")

# 2. Configuração da página executiva
st.set_page_config(
    page_title="SuperDash - Monitoramento de Refrigeração",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. Estilização Executiva (Header & KPI Cards)
st.markdown("""
    <style>
        .main { background-color: #F8FAFC; }
        
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
        
        .kpi-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px 20px;
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
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1;
        }
        .kpi-footer {
            font-size: 11px;
            color: #64748B;
            margin-top: 6px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
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

# 4. Carregamento e filtros de dados
df_raw = load_and_normalize_data()

if df_raw.empty:
    st.error("⚠️ Não foi possível carregar os dados. Verifique a conexão com a planilha.")
    st.stop()

filter_output = render_sidebar_filters(df_raw)
df_filtered = filter_output[0] if isinstance(filter_output, tuple) else filter_output

# --- TOPO EXECUTIVO: CABEÇALHO & CARDS DE KPI ---
st.markdown("""
    <div class="exec-header-container">
        <div class="exec-header-title">❄️ SuperDash - Monitoramento & Inteligência de Refrigeração</div>
        <div class="exec-header-subtitle">Painel Integrado de Gestão de Ativos, Manutenções e Cobertura de Garantias</div>
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

# Helper seguro para execução das telas
def safe_render(module, df):
    if module is None:
        st.warning("Módulo da aba não encontrado no projeto.")
        return
    for func_name in ["render_monitoramento", "render_maquinas", "render_corretivas", "render_clientes_regioes", "render_analise_tarefas", "render", "main"]:
        if hasattr(module, func_name):
            getattr(module, func_name)(df)
            return
    st.info("Visão sem função pública de renderização encontrada.")

# --- NAVEGAÇÃO POR ABAS COM TODAS AS FUNCIONALIDADES PRESERVADAS ---
tab_mon, tab_maq, tab_corr, tab_cli, tab_taref, tab_raw = st.tabs([
    "📊 Monitoramento Geral", 
    "⚙️ Máquinas & Comparativos", 
    "🚨 Manutenções Corretivas", 
    "🏢 Clientes & Regiões", 
    "📝 Análise de Tarefas",
    "📋 Tabela Operacional"
])

with tab_mon:
    safe_render(v_mon, df_filtered)

with tab_maq:
    safe_render(v_maq, df_filtered)

with tab_corr:
    safe_render(v_corr, df_filtered)

with tab_cli:
    safe_render(v_cli, df_filtered)

with tab_taref:
    safe_render(v_tar, df_filtered)

with tab_raw:
    st.subheader("Base Operacional Completa")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
