import pandas as pd
import streamlit as st

from data_loader import load_and_normalize_data
from filters import (
    render_sidebar_filters,
    import_state_from_url,
    export_state_to_url,
)
try:
    from ui import apply_theme
except SyntaxError as error:
    import traceback
    st.error(f"SyntaxError em: {error.filename} (linha {error.lineno})")
    st.code(traceback.format_exc())
    st.stop()
    

st.set_page_config(
    page_title="Painel de Refrigeração",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

pages = [
    st.Page("views/monitoramento.py",    title="Visão geral",         icon="📊", default=True),
    st.Page("views/corretivas.py",       title="Corretivas",          icon="🔧"),
    st.Page("views/analise_tarefas.py",  title="Operação",            icon="⚙️"),
    st.Page("views/maquinas.py",         title="Equipamentos",        icon="❄️"),
    st.Page("views/clientes_regioes.py", title="Clientes e regiões",  icon="🏢"),
]
page = st.navigation(pages, position="top")

try:
    raw = load_and_normalize_data()
    st.session_state["_data_loaded_at"] = pd.Timestamp.now()
except Exception as error:
    st.error(
        "Não foi possível carregar os dados. Nenhum resultado parcial será apresentado."
    )
    with st.expander("Diagnóstico da leitura"):
        st.code(str(error))
    st.stop()

if raw.empty:
    st.info("A base não contém tarefas disponíveis.")
    st.stop()

import_state_from_url(raw)

cut, valid, additional, spec = render_sidebar_filters(raw)
st.session_state["_page_context"] = dict(
    raw=raw,
    cut=cut,
    valid=valid,
    additional=additional,
    spec=spec,
)

export_state_to_url(spec)

page.run()
