import sys
import os
import streamlit as st
import pandas as pd

# 1. Ajuste de caminhos para a pasta 'view'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIEW_DIR = os.path.join(BASE_DIR, "view")
VIEWS_DIR = os.path.join(BASE_DIR, "views")

for d in [BASE_DIR, VIEW_DIR, VIEWS_DIR]:
    if os.path.exists(d) and d not in sys.path:
        sys.path.insert(0, d)

# 2. Configuração de Página
st.set_page_config(
    page_title="SuperDash - Monitoramento Executivo",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. Importação de Módulos Base e UI Executiva
from data_loader import load_and_normalize_data
from filters import render_sidebar_filters
from kpis import calculate_executive_kpis
import ui

ui.apply_executive_ui()

# 4. Importação defensiva dos módulos das visões
try:
    import view.monitoramento as v_mon
    import view.maquinas as v_maq
    import view.corretivas as v_corr
    import view.clientes_regioes as v_cli
    import view.analise_tarefas as v_tar
except ImportError:
    try:
        import views.monitoramento as v_mon
        import views.maquinas as v_maq
        import views.corretivas as v_corr
        import views.clientes_regioes as v_cli
        import views.analise_tarefas as v_tar
    except ImportError:
        v_mon = v_maq = v_corr = v_cli = v_tar = ui

# 5. Carregamento dos dados brutos
df_raw = load_and_normalize_data()

if df_raw.empty:
    st.error("⚠️ Não foi possível carregar os dados. Verifique a planilha.")
    st.stop()

# 6. Processamento dos Filtros
filter_output = render_sidebar_filters(df_raw)
df_filtered = filter_output[0] if isinstance(filter_output, tuple) else filter_output

# --- TOPO EXECUTIVO ---
ui.render_executive_header(
    title="❄️ SuperDash - Monitoramento Executivo de Refrigeração",
    subtitle="Painel Integrado de Inteligência Operacional, Comparativos de Ativos e Cobertura de Garantias"
)

kpis = calculate_executive_kpis(df_filtered)

c1, c2, c3, c4 = st.columns(4)
with c1:
    ui.render_kpi_card("Total de Atendimentos", f"{kpis['total_chamados']:,}", "📋 Registros no período", "primary")
with c2:
    ui.render_kpi_card("Preventivas", f"{kpis['preventivas']:,}", f"🟢 {kpis['pct_preventivas']:.1f}% de eficiência", "success")
with c3:
    ui.render_kpi_card("Corretivas", f"{kpis['corretivas']:,}", "🟠 Reparos e emergências", "warning")
with c4:
    var_gar = "success" if kpis['pct_garantia'] >= 30 else "danger"
    ui.render_kpi_card("Em Garantia", f"{kpis['pct_garantia']:.1f}%", f"🛡️ {kpis['garantia_qtd']} ativo(s) cobertos", var_gar)

st.write("")

# Helper para executar o render das telas com total resiliência
def execute_view(mod, fallback_func, df):
    for func_name in ["render_monitoramento", "render_maquinas", "render_corretivas", "render_clientes_regioes", "render_analise_tarefas", "render", "main"]:
        if hasattr(mod, func_name):
            getattr(mod, func_name)(df)
            return
    fallback_func(df)

# --- NAVEGAÇÃO EXECUTIVA POR ABAS FLUIDAS ---
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📊 Monitoramento Geral", 
    "⚙️ Máquinas & Comparativos", 
    "🚨 Manutenções Corretivas", 
    "🏢 Clientes & Regiões", 
    "📝 Análise de Tarefas",
    "📋 Base de Dados Operacional"
])

with t1:
    execute_view(v_mon, ui.render_monitoramento, df_filtered)

with t2:
    execute_view(v_maq, ui.render_maquinas, df_filtered)

with t3:
    execute_view(v_corr, ui.render_corretivas, df_filtered)

with t4:
    execute_view(v_cli, ui.render_clientes_regioes, df_filtered)

with t5:
    execute_view(v_tar, ui.render_analise_tarefas, df_filtered)

with t6:
    st.subheader("Base de Dados Operacional Completa")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
