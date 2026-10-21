import streamlit as st
import pandas as pd
import plotly.express as px

# Importações dos módulos do SuperDash
from data_loader import load_and_normalize_data
from filters import render_sidebar_filters
from kpis import calculate_executive_kpis

# 1. Configuração da página e estilo executivo
st.set_page_config(
    page_title="Painel Executivo & Analítico de Manutenção",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CSS Executivo para Cabeçalho, Cards e Abas
st.markdown("""
    <style>
        .exec-header-container {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            padding: 24px 32px;
            border-radius: 14px;
            color: #FFFFFF;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
        }
        .exec-header-title {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin: 0;
            color: #FFFFFF;
        }
        .exec-header-subtitle {
            font-size: 14px;
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
            font-size: 12px;
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
            font-size: 12px;
            color: #64748B;
            margin-top: 8px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #F1F5F9;
            padding: 6px;
            border-radius: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #0284C7 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# 3. Carregamento e Filtros
df_raw = load_and_normalize_data()

if df_raw.empty:
    st.error("⚠️ Não foi possível carregar os dados. Verifique a conexão com a planilha.")
    st.stop()

filter_output = render_sidebar_filters(df_raw)
df_filtered = filter_output[0] if isinstance(filter_output, tuple) else filter_output

# --- TOPO: CABEÇALHO E CARDS DE KPI ---
st.markdown("""
    <div class="exec-header-container">
        <div class="exec-header-title">🏢 Executive Operations Dashboard</div>
        <div class="exec-header-subtitle">Inteligência de manutenção, análises comparativas e gestão de ativos</div>
    </div>
""", unsafe_allow_html=True)

kpis = calculate_executive_kpis(df_filtered)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
        <div class="kpi-card kpi-border-primary">
            <div class="kpi-label">Volume de Atendimentos</div>
            <div class="kpi-value">{kpis['total_chamados']:,}</div>
            <div class="kpi-footer">📋 Registros no período</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="kpi-card kpi-border-success">
            <div class="kpi-label">Manutenções Preventivas</div>
            <div class="kpi-value">{kpis['preventivas']:,}</div>
            <div class="kpi-footer">🟢 {kpis['pct_preventivas']:.1f}% das operações</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="kpi-card kpi-border-warning">
            <div class="kpi-label">Atendimentos Corretivos</div>
            <div class="kpi-value">{kpis['corretivas']:,}</div>
            <div class="kpi-footer">🟠 Intervenções de reparo</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    variant_gar = "kpi-border-success" if kpis['pct_garantia'] >= 30 else "kpi-border-danger"
    st.markdown(f"""
        <div class="kpi-card {variant_gar}">
            <div class="kpi-label">Equipamentos em Garantia</div>
            <div class="kpi-value">{kpis['pct_garantia']:.1f}%</div>
            <div class="kpi-footer">🛡️ {kpis['garantia_qtd']} ativo(s) cobertos</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# --- ESTRUTURA DE ABAS PARA ANÁLISES E COMPARATIVOS ---
tab_macro, tab_comparativo, tab_tecnica, tab_relatorio = st.tabs([
    "📈 Visão Estratégica & Gráficos", 
    "⚔️ Comparativo de Máquinas", 
    "🛠️ Performance de Técnicos & Garantias", 
    "📋 Base Operacional Completa"
])

# --- ABA 1: VISÃO ESTRATÉGICA E GRÁFICOS ---
with tab_macro:
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Distribuição por Tipo de Manutenção")
        if "Tipo" in df_filtered.columns and not df_filtered.empty:
            df_tipo = df_filtered["Tipo"].value_counts().reset_index()
            df_tipo.columns = ["Tipo", "Quantidade"]
            fig_pie = px.pie(
                df_tipo, 
                names="Tipo", 
                values="Quantidade", 
                hole=0.45,
                color_discrete_sequence=["#0284C7", "#F59E0B", "#16A34A", "#DC2626"]
            )
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=340)
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.subheader("Top 5 Falhas / Problemas Recorrentes")
        if "Problema" in df_filtered.columns and not df_filtered.empty:
            df_prob = df_filtered["Problema"].value_counts().head(5).reset_index()
            df_prob.columns = ["Problema", "Quantidade"]
            fig_bar = px.bar(
                df_prob, 
                x="Quantidade", 
                y="Problema", 
                orientation="h",
                color="Quantidade",
                color_continuous_scale="Blues"
            )
            fig_bar.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20, l=20, r=20), height=340)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    # Evolução Temporal dos Atendimentos
    st.subheader("Evolução de Atendimentos ao Longo do Tempo")
    if "Data da tarefa" in df_filtered.columns and not df_filtered.empty:
        df_temp = df_filtered.dropna(subset=["Data da tarefa"]).copy()
        if not df_temp.empty:
            df_temp["Mês/Ano"] = df_temp["Data da tarefa"].dt.to_period("M").astype(str)
            df_trend = df_temp.groupby(["Mês/Ano", "Tipo"]).size().reset_index(name="Atendimentos")
            fig_trend = px.line(
                df_trend, 
                x="Mês/Ano", 
                y="Atendimentos", 
                color="Tipo",
                markers=True,
                color_discrete_map={"Preventiva": "#16A34A", "Corretiva": "#F59E0B"}
            )
            fig_trend.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_trend, use_container_width=True)

# --- ABA 2: COMPARATIVO DE MÁQUINAS ---
with tab_comparativo:
    st.subheader("⚔️ Análise Comparativa de Equipamentos (Máquinas)")
    st.caption("Selecione duas ou mais máquinas para comparar o histórico operacional e incidência de corretivas.")

    if "Máquina" in df_filtered.columns and not df_filtered.empty:
        maquinas_disponiveis = sorted([m for m in df_filtered["Máquina"].dropna().unique() if m != "Não especificado"])
        
        selected_maquinas = st.multiselect(
            "Selecione as máquinas para comparação:",
            options=maquinas_disponiveis,
            default=maquinas_disponiveis[:2] if len(maquinas_disponiveis) >= 2 else maquinas_disponiveis
        )

        if selected_maquinas:
            df_comp = df_filtered[df_filtered["Máquina"].isin(selected_maquinas)]
            
            # Gráfico Comparativo 1: Volume por Tipo de Manutenção
            col_comp1, col_comp2 = st.columns(2)
            
            with col_comp1:
                st.markdown("**Atendimentos por Máquina e Tipo**")
                df_comp_tipo = df_comp.groupby(["Máquina", "Tipo"]).size().reset_index(name="Quantidade")
                fig_comp_bar = px.bar(
                    df_comp_tipo, 
                    x="Máquina", 
                    y="Quantidade", 
                    color="Tipo",
                    barmode="group",
                    color_discrete_sequence=["#0284C7", "#F59E0B", "#16A34A"]
                )
                fig_comp_bar.update_layout(height=340)
                st.plotly_chart(fig_comp_bar, use_container_width=True)

            with col_comp2:
                st.markdown("**Distribuição de Falhas nas Máquinas Selecionadas**")
                df_comp_prob = df_comp.groupby(["Máquina", "Problema"]).size().reset_index(name="Quantidade")
                fig_comp_prob = px.bar(
                    df_comp_prob, 
                    x="Quantidade", 
                    y="Máquina", 
                    color="Problema",
                    orientation="h"
                )
                fig_comp_prob.update_layout(height=340)
                st.plotly_chart(fig_comp_prob, use_container_width=True)

            # Tabela Resumo Lado a Lado
            st.markdown("**Resumo Executivo do Comparativo**")
            resumo_list = []
            for m in selected_maquinas:
                sub = df_comp[df_comp["Máquina"] == m]
                resumo_list.append({
                    "Máquina": m,
                    "Total Chamados": len(sub),
                    "Preventivas": len(sub[sub["Tipo"].str.contains("Preventiva", case=False, na=False)]),
                    "Corretivas": len(sub[sub["Tipo"].str.contains("Corretiva", case=False, na=False)]),
                    "Principal Problema": sub["Problema"].mode()[0] if not sub["Problema"].empty else "N/A",
                    "Garantia": sub["Garantia"].iloc[0] if "Garantia" in sub.columns and not sub.empty else "N/A"
                })
            
            st.dataframe(pd.DataFrame(resumo_list), use_container_width=True, hide_index=True)
        else:
            st.info("Selecione ao menos uma máquina no campo acima para gerar a análise.")

# --- ABA 3: DESEMPENHO TÉCNICO & GARANTIAS ---
with tab_tecnica:
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.subheader("Atendimentos por Técnico")
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
        st.subheader("Status do Parque referente à Garantia")
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

# --- ABA 4: RELATÓRIO COMPLETO ---
with tab_relatorio:
    st.subheader("📋 Base de Dados Operacional Filtrada")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
