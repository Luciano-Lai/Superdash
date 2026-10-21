from html import escape

import pandas as pd
import streamlit as st

from data_loader import clean, norm


INVALID = {"", "nenhuma", "nenhum", "nao informado", "nan", "none", "<na>"}

KPI_BAD_WHEN_UP = {
    "Corretivas", "% Corretivas",
    "Corretivas em garantia", "Corretivas fora da garantia",
}
KPI_GOOD_WHEN_UP = {"Preventivas", "% Preventivas"}

TOOLTIPS = {
    "Total de tarefas": "Todas as tarefas do recorte atual.",
    "Preventivas": "Tarefas com Tipo = Preventiva.",
    "Corretivas": "Tarefas com Tipo = Corretiva.",
    "% Preventivas":
        "Proporção de preventivas no total do recorte. "
        "O delta é em pontos percentuais (p.p.), não em variação relativa.",
    "% Corretivas":
        "Proporção de corretivas no total do recorte. "
        "O delta é em pontos percentuais (p.p.), não em variação relativa.",
    "Máquinas atendidas": "Máquinas distintas com pelo menos uma tarefa.",
    "Técnicos envolvidos": "Técnicos distintos com pelo menos uma tarefa.",
    "Corretivas em garantia":
        "Situação atual da data limite. Não representa a cobertura "
        "histórica da chamada.",
    "Corretivas fora da garantia":
        "Situação atual da data limite. Não representa a cobertura "
        "histórica da chamada.",
    "Problema mais frequente":
        "Considera apenas corretivas com problema válido.",
    "Peça mais trocada":
        "Considera apenas corretivas com peça válida.",
}

KPI_ICONS = {
    "Total de tarefas": "📋",
    "Preventivas": "🛡️",
    "Corretivas": "🔧",
    "% Preventivas": "📊",
    "% Corretivas": "📊",
    "Máquinas atendidas": "❄️",
    "Técnicos envolvidos": "👥",
    "Corretivas em garantia": "✅",
    "Corretivas fora da garantia": "⚠️",
    "Problema mais frequente": "⚡",
    "Peça mais trocada": "⚙️",
}

NUMERIC_KPIS = {
    "Total de tarefas", "Preventivas", "Corretivas",
    "Máquinas atendidas", "Técnicos envolvidos",
    "Corretivas em garantia", "Corretivas fora da garantia",
}
PERCENT_KPIS = {"% Preventivas", "% Corretivas"}
TEXT_KPIS = {"Problema mais frequente", "Peça mais trocada"}


def _as_number(value):
    """
    Converte o valor do KPI em float quando possível.
    Aceita números crus e strings no formato '45,0%'.
    Retorna None se não for numérico ('—', texto).
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.endswith("%"):
            try:
                return float(cleaned.replace("%", "").replace(",", ".").strip())
            except ValueError:
                return None
    return None


def occurrence_frame(df, column):
    out = df.loc[df["Tipo"].eq("Corretiva")].copy()
    out[column] = out[column].map(
        lambda v: clean(v).replace("\n", ";").split(";")
    )
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
        "% Preventivas": (
            f"{prev / total * 100:.1f}%".replace(".", ",") if total else "—"
        ),
        "% Corretivas": (
            f"{len(corr) / total * 100:.1f}%".replace(".", ",")
            if total
            else "—"
        ),
        "Máquinas atendidas": df.loc[df["Máquina"].ne(""), "Máquina"].nunique(),
        "Técnicos envolvidos": df.loc[df["Técnico"].ne(""), "Técnico"].nunique(),
        "Corretivas em garantia": int(corr["Garantia"].eq("Dentro").sum()),
        "Corretivas fora da garantia": int(corr["Garantia"].eq("Fora").sum()),
        "Problema mais frequente": frequent("Problema"),
        "Peça mais trocada": frequent("Peça"),
    }


def calculate_kpis_with_delta(df, previous_df=None):
    """
    Retorna (values, deltas, previous).

    deltas[name] é:
      - variação relativa em % (para contagens numéricas)
      - diferença em pontos percentuais (p.p.) para KPIs de taxa
    """
    current = calculate_kpis(df)
    if previous_df is None or previous_df.empty:
        return current, {}, {}

    previous = calculate_kpis(previous_df)
    deltas = {}

    for name, value in current.items():
        if name in TEXT_KPIS:
            continue

        cur_num = _as_number(value)
        prev_num = _as_number(previous.get(name))

        if cur_num is None or prev_num is None:
            continue

        if name in PERCENT_KPIS:
            # Taxa: diferença em pontos percentuais
            deltas[name] = cur_num - prev_num
        else:
            # Contagem: variação relativa
            if prev_num > 0:
                deltas[name] = (cur_num - prev_num) / prev_num * 100

    return current, deltas, previous


def compute_kpi_series(raw, effective_spec, buckets=6):
    from filters import apply_filters

    period = effective_spec.get("period")
    if not (isinstance(period, (tuple, list)) and len(period) == 2):
        return {}
    try:
        start, end = map(pd.Timestamp, period)
    except Exception:
        return {}
    duration = (end - start).days + 1
    if duration <= 0:
        return {}

    series = {}
    for i in range(buckets, 0, -1):
        b_end = start - pd.Timedelta(days=(i - 1) * duration)
        b_start = b_end - pd.Timedelta(days=duration - 1)
        b_spec = {
            **effective_spec,
            "period": (b_start.date(), b_end.date()),
        }
        b_df = apply_filters(raw, b_spec)
        b_kpis = calculate_kpis(b_df)
        for name, value in b_kpis.items():
            series.setdefault(name, []).append(value)

    cur_df = apply_filters(raw, effective_spec)
    cur_kpis = calculate_kpis(cur_df)
    for name, value in cur_kpis.items():
        series.setdefault(name, []).append(value)

    return series


def _sparkline_svg(values, color="#0284C7", height=44):
    numeric = [
        float(v) for v in values
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    if len(numeric) < 3:
        return ""

    n = len(numeric)
    min_v, max_v = min(numeric), max(numeric)
    if max_v == min_v:
        max_v = min_v + 1

    w, h = 100, height
    points = []
    for i, v in enumerate(numeric):
        x = (i / (n - 1)) * w
        y = h - ((v - min_v) / (max_v - min_v)) * (h - 8) - 4
        points.append(f"{x:.1f},{y:.1f}")

    poly = " ".join(points)
    area = f"0,{h} {poly} {w},{h}"
    grad_id = f"sg{abs(hash(tuple(numeric))) % 100000}"

    return (
        f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
        f'style="width:100%;height:{h}px;display:block;margin:4px 0 0 0">'
        f'<defs>'
        f'<linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.28"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<polygon points="{area}" fill="url(#{grad_id})"/>'
        f'<polyline points="{poly}" fill="none" stroke="{color}" '
        f'stroke-width="2.2" vector-effect="non-scaling-stroke" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'</svg>'
    )


def _border_and_delta_class(name, delta):
    if delta is None:
        return "kpi-border-primary", "kpi-delta-flat"
    if name in KPI_BAD_WHEN_UP:
        if delta > 0:
            return "kpi-border-danger", "kpi-delta-bad"
        if delta < 0:
            return "kpi-border-success", "kpi-delta-good"
        return "kpi-border-neutral", "kpi-delta-flat"
    if name in KPI_GOOD_WHEN_UP:
        if delta > 0:
            return "kpi-border-success", "kpi-delta-good"
        if delta < 0:
            return "kpi-border-danger", "kpi-delta-bad"
        return "kpi-border-neutral", "kpi-delta-flat"
    return "kpi-border-primary", "kpi-delta-flat"


def build_kpi_card(name, values, deltas, series, previous):
    value = values.get(name, "—")
    delta = deltas.get(name)
    prev_val = previous.get(name)
    border, delta_class = _border_and_delta_class(name, delta)

    if name in TEXT_KPIS:
        val_class = "kpi-value-text"
        display = str(value) if str(value).strip() else "—"
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        val_class = "kpi-value"
        display = f"{int(value):,}".replace(",", ".")
    else:
        val_class = "kpi-value"
        display = str(value)

    # ---------- Badge de delta (topo direito) ----------
    delta_html = ""
    if name not in TEXT_KPIS:
        if delta is not None:
            arrow = "▲" if delta > 0 else "▼" if delta < 0 else "≡"
            if name in PERCENT_KPIS:
                d_fmt = f"{abs(delta):.1f} p.p.".replace(".", ",")
                title = "Diferença em pontos percentuais vs período anterior"
            else:
                d_fmt = f"{abs(delta):.1f}%".replace(".", ",")
                title = "Variação relativa vs período anterior"
            delta_html = (
                f'<span class="kpi-delta {delta_class}" title="{escape(title)}">'
                f'{arrow} {d_fmt}</span>'
            )
        else:
            delta_html = (
                '<span class="kpi-delta kpi-delta-flat" '
                'title="Sem período anterior comparável. Reduza a data '
                'inicial no filtro Período.">'
                'sem base</span>'
            )

    # ---------- Visualização interna ----------
    viz_html = ""
    if name in PERCENT_KPIS:
        pct = _as_number(value)
        if pct is not None:
            width = max(0, min(100, pct))
            if name == "% Corretivas":
                color = (
                    "#DC2626" if pct > 40
                    else "#F59E0B" if pct > 25
                    else "#16A34A"
                )
            else:
                color = (
                    "#16A34A" if pct >= 60
                    else "#F59E0B" if pct >= 30
                    else "#DC2626"
                )
            viz_html = (
                f'<div class="kpi-progress">'
                f'<div class="kpi-progress-fill" '
                f'style="width:{width}%;background:{color}"></div>'
                f'</div>'
            )
    elif name in NUMERIC_KPIS and name in series:
        svg = _sparkline_svg(
            series[name],
            color=(
                "#DC2626" if border == "kpi-border-danger"
                else "#16A34A" if border == "kpi-border-success"
                else "#0284C7"
            ),
        )
        if svg:
            viz_html = f'<div class="kpi-sparkline">{svg}</div>'

    # ---------- Rodapé (valor anterior) ----------
    footer = ""
    if name not in TEXT_KPIS:
        prev_num = _as_number(prev_val)
        if prev_num is not None:
            if name in PERCENT_KPIS:
                prev_disp = f"{prev_num:.1f}%".replace(".", ",")
            else:
                prev_disp = f"{int(prev_num):,}".replace(",", ".")
            footer = f"vs {prev_disp} no período anterior"
    elif name in TEXT_KPIS and str(value).strip() not in {"—", ""}:
        footer = "no recorte atual"

    icon = KPI_ICONS.get(name, "")
    help_text = TOOLTIPS.get(name, "")
    help_attr = (
        f' title="{escape(help_text, quote=True)}"'
        if help_text else ""
    )

    return (
        f'<div class="kpi-card {border}">'
        f'<div class="kpi-header">'
        f'<span class="kpi-label"{help_attr}>{icon} {escape(name)}</span>'
        f'{delta_html}'
        f'</div>'
        f'<div class="kpi-value-row">'
        f'<span class="{val_class}">{escape(display)}</span>'
        f'</div>'
        f'{viz_html}'
        f'<div class="kpi-footer">{escape(footer)}</div>'
        f'</div>'
    )


def render_kpi_cards(selected_kpis, values, deltas=None, series=None, previous=None):
    deltas = deltas or {}
    series = series or {}
    previous = previous or {}
    for start in range(0, len(selected_kpis), 4):
        group = selected_kpis[start:start + 4]
        columns = st.columns(4)
        for col, name in zip(columns, group):
            col.markdown(
                build_kpi_card(name, values, deltas, series, previous),
                unsafe_allow_html=True,
            )
