import streamlit as st
import pandas as pd
import plotly.express as px

def apply_executive_ui():
    """Injeta regras CSS para visual executivo C-Level."""
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
            
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
            }
            .main {
                background-color: #F8FAFC;
            }
            #MainMenu, footer, header {visibility: hidden;}
            
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

def render_executive_header(title: str, subtitle: str):
    st.markdown(f"""
        <div class="exec-header-container">
            <div class="exec-header-title">{title}</div>
            <div class="exec-header-subtitle">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

def render_kpi_card(title: str, value: str, footer: str = "", variant: str = "primary"):
    st.markdown(f"""
        <div class="kpi-card kpi-border-{variant}">
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-footer">{footer}</div>
        </div>
    """, unsafe_allow_html=True)

def render_monitoramento(df):
    st.subheader("📊 Visão Consolidada de Operações")
    c1, c2 = st.columns(2)
    with c1:
        if "Tipo" in df.columns and not df.empty:
            df_t = df["Tipo"].value_counts().reset_index()
            df_t.columns = ["Tipo", "Qtd"]
            fig = px.pie(df_t, names="Tipo", values="Qtd", hole=0.4, title="Manutenções por Tipo")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if "Problema" in df.columns and not df.empty:
            df_p = df["Problema"].value_counts().head(5).reset_index()
            df_p.columns = ["Problema", "Qtd"]
            fig = px.bar(df_p, x="Qtd", y="Problema", orientation="h", title="Top Problemas Relatados")
            st.plotly_chart(fig, use_container_width=True)

def render_maquinas(df):
    st.subheader("⚙️ Gestão & Comparativo de Máquinas")
    if "Máquina" in df.columns and not df.empty:
        opcoes = sorted([m for m in df["Máquina"].dropna().unique() if str(m).strip() != ""])
        sel = st.multiselect("Selecione os equipamentos para comparação lado a lado:", opcoes, default=opcoes[:2] if len(opcoes)>=2 else opcoes)
        if sel:
            df_sel = df[df["Máquina"].isin(sel)]
            c1, c2 = st.columns(2)
            with c1:
                df_m = df_sel.groupby(["Máquina", "Tipo"]).size().reset_index(name="Atendimentos")
                fig = px.bar(df_m, x="Máquina", y="Atendimentos", color="Tipo", barmode="group", title="Atendimentos por Máquina e Tipo")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                df_p = df_sel.groupby(["Máquina", "Problema"]).size().reset_index(name="Qtd")
                fig = px.bar(df_p, x="Qtd", y="Máquina", color="Problema", orientation="h", title="Ocorrências por Equipamento")
                st.plotly_chart(fig, use_container_width=True)

def render_corretivas(df):
    st.subheader("🚨 Análise Detalhada de Intervenções Corretivas")
    if "Tipo" in df.columns:
        df_corr = df[df["Tipo"].astype(str).str.contains("Corretiva", case=False, na=False)]
        st.dataframe(df_corr, use_container_width=True, hide_index=True)

def render_clientes_regioes(df):
    st.subheader("🏢 Distribuição por Clientes & Regiões")
    col = "Cliente" if "Cliente" in df.columns else ("Região" if "Região" in df.columns else None)
    if col and not df.empty:
        df_c = df[col].value_counts().reset_index()
        df_c.columns = [col, "Atendimentos"]
        fig = px.bar(df_c, x=col, y="Atendimentos", title=f"Volume de Chamados por {col}")
        st.plotly_chart(fig, use_container_width=True)

def render_analise_tarefas(df):
    st.subheader("📝 Indicadores Operacionais de Tarefas")
    if "Técnico" in df.columns and not df.empty:
        df_t = df["Técnico"].value_counts().reset_index()
        df_t.columns = ["Técnico", "Tarefas"]
        fig = px.bar(df_t, x="Técnico", y="Tarefas", title="Produtividade por Técnico")
        st.plotly_chart(fig, use_container_width=True)
