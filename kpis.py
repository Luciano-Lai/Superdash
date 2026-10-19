import streamlit as st
import pandas as pd

def calculate_kpis(df):
    total = len(df)
    preventivas = len(df[df["Tipo"] == "Preventiva"])
    corretivas = len(df[df["Tipo"] == "Corretiva"])

    perc_prev = f"{(preventivas / total * 100):.1f}%" if total > 0 else "—"
    perc_corr = f"{(corretivas / total * 100):.1f}%" if total > 0 else "—"

    maquinas = df["Máquina"].nunique()
    tecnicos = df["Técnico"].nunique()

    df_corr = df[df["Tipo"] == "Corretiva"]
    em_garantia = len(df_corr[df_corr["Garantia"] == "Dentro"])
    fora_garantia = len(df_corr[df_corr["Garantia"] == "Fora"])

    prob_series = df_corr["Problema"].dropna().astype(str).str.split(";").explode().str.strip()
    prob_series = prob_series[prob_series != "Não informado"]
    prob_mais_freq = prob_series.mode()[0] if not prob_series.empty else "—"

    peca_series = df["Peça"].dropna().astype(str).str.split(";").explode().str.strip()
    peca_series = peca_series[~peca_series.isin(["Nenhuma", "Não informado"])]
    peca_mais_trocada = peca_series.mode()[0] if not peca_series.empty else "—"

    return {
        "Total de tarefas": total,
        "Preventivas": preventivas,
        "Corretivas": corretivas,
        "% Preventivas": perc_prev,
        "% Corretivas": perc_corr,
        "Máquinas atendidas": maquinas,
        "Técnicos envolvidos": tecnicos,
        "Corretivas em garantia": em_garantia,
        "Corretivas fora da garantia": fora_garantia,
        "Problema mais frequente": prob_mais_freq,
        "Peça mais trocada": peca_mais_trocada
    }

def render_kpi_cards(selected_kpis, kpi_values):
    if not selected_kpis:
        return

    cols = st.columns(min(len(selected_kpis), 4))
    for idx, kpi_name in enumerate(selected_kpis):
        col = cols[idx % 4]
        val = kpi_values.get(kpi_name, "—")
        col.metric(label=kpi_name, value=val)
