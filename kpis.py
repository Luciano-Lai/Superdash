from html import escape
import pandas as pd
import streamlit as st
from data_loader import clean, norm

INVALID = {"", "nenhuma", "nenhum", "nao informado", "nan", "none", "<na>"}

TOOLTIPS = {
    "Corretivas em garantia":
        "Situação atual da data limite. Não representa a cobertura histórica da chamada.",
    "Corretivas fora da garantia":
        "Situação atual da data limite. Não representa a cobertura histórica da chamada.",
    "Problema mais frequente": "Considera apenas corretivas com problema válido.",
    "Peça mais trocada": "Considera apenas corretivas com peça válida.",
    "% Preventivas": "Proporção de preventivas no total do recorte.",
    "% Corretivas": "Proporção de corretivas no total do recorte.",
}

NEGATIVE_IS_BAD = {
    "Corretivas", "% Corretivas",
    "Corretivas em garantia", "Corretivas fora da garantia",
}


def occurrence_frame(df, column):
    out = df.loc[df["Tipo"].eq("Corretiva")].copy()
    out[column] = out[column].map(lambda v: clean(v).replace("\n", ";").split(";"))
    out = out.explode(column)
    out[column] = out[column].map(clean)
    return out.loc[~out[column].map(norm).isin(INVALID)].copy()


def calculate_kpis(df):
    total = len(df)
    prev = int(df["Tipo"].eq("Preventiva").sum())
    corr = df.loc[df["Tipo"].eq("Corretiva")]

    def frequent(column):
        counts = occurrence_frame(df, column)[column].value_counts()
        return str(counts.index[0]) if not counts.empty else "—"

    return {
        "Total de tarefas": total,
        "Preventivas": prev,
        "Corretivas": len(corr),
        "% Preventivas": f"{prev / total * 100:.1f}%".replace(".", ",") if total else "—",
        "% Corretivas": f"{len(corr) / total * 100:.1f}%".replace(".", ",") if total else "—",
        "Máquinas atendidas": df.loc[df["Máquina"].ne(""), "Máquina"].nunique(),
        "Técnicos envolvidos": df.loc[df["Técnico"].ne(""), "Técnico"].nunique(),
        "Corretivas em garantia": int(corr["Garantia"].eq("Dentro").sum()),
        "Corretivas fora da garantia": int(corr["Garantia"].eq("Fora").sum()),
        "Problema mais frequente": frequent("Problema"),
        "Peça mais trocada": frequent("Peça"),
    }


def calculate_kpis_with_delta(df, previous_df=None):
    current = calculate_kpis(df)
    if previous_df is None or previous_df.empty:
        return current, {}
    previous = calculate_kpis(previous_df)
    deltas = {}
    for name, value in current.items():
        pv = previous.get(name)
        if (
            isinstance(value, (int, float)) and not isinstance(value, bool)
            and isinstance(pv, (int, float)) and not isinstance(pv, bool)
            and pv > 0
        ):
            deltas[name] = (value - pv) / pv * 100
    return current, deltas


def render_kpi_cards(selected_kpis, values, deltas=None):
    deltas = deltas or {}
    for start in range(0, len(selected_kpis), 4):
        group = selected_kpis[start:start + 4]
        columns = st.columns(4)
        for col, name in zip(columns, group):
            value = values.get(name, "—")
            is_text = name in {"Problema mais frequente", "Peça mais trocada"}
            display = (
                f"{int(value):,}".replace(",", ".")
                if isinstance(value, (int, float)) else str(value)
            )
            size = "1rem" if is_text else "2rem"
            help_text = TOOLTIPS.get(name, "")
            help_attr = f' title="{escape(help_text, quote=True)}"' if help_text else ""
            marker = " ⓘ" if help_text else ""

            delta_html = ""
            if name in deltas and not is_text:
                d = deltas[name]
                arrow = "▲" if d > 0 else "▼" if d < 0 else "＝"
                if name in NEGATIVE_IS_BAD:
                    color = "#C0392B" if d > 0 else "#31889A" if d < 0 else "#6B7B8E"
                else:
                    color = "#31889A" if d > 0 else "#C0392B" if d < 0 else "#6B7B8E"
                d_fmt = f"{abs(d):.1f}".replace(".", ",")
                delta_html = (
                    f'<div style="font-size:.78rem;color:{color};margin-top:4px">'
                    f'{arrow} {d_fmt}% vs período anterior</div>'
                )

            html = (
                f'<div class="kpi-card">'
                f'<div class="kpi-label"{help_attr}>{escape(name)}{marker}</div>'
                f'<div class="kpi-value" style="font-size:{size}">{escape(display)}</div>'
                f'{delta_html}'
                f'</div>'
            )
            col.markdown(html, unsafe_allow_html=True)
