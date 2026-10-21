import hashlib
import math
import unicodedata
from html import escape

import pandas as pd
import streamlit as st

from charts import (
    render_evolution_chart,
    render_horizontal_ranking,
    render_donut_chart,
    render_pareto_chart,
    render_abc_donut,
    abc_table,
    category_counts,
    revise_bar_labels,
)
from filters import COLUMNS, previous_period
from kpis import (
    calculate_kpis,
    render_kpi_cards,
    occurrence_frame,
    calculate_kpis_with_delta,
    compute_kpi_series,
)
from pdf_export import generate_pdf_report
from comparison import (
    comparison_base,
    split_machines,
    comparison_evolution,
    comparison_bars,
    comparison_share,
    comparison_occurrences,
    MAX_MACHINES,
)


EXECUTIVE_PRESETS = {
    "monitoramento": {
        "kpis": [
            "Total de tarefas", "Preventivas", "Corretivas",
            "% Corretivas", "Máquinas atendidas", "Técnicos envolvidos",
        ],
        "charts": [
            "Evolução da operação",
            "Composição das manutenções",
            "Máquinas por classe ABC",
        ],
    },
    "corretivas": {
        "kpis": [
            "Corretivas", "Problema mais frequente",
            "Peça mais trocada", "Corretivas em garantia",
        ],
        "charts": [
            "Falhas relatadas",
            "Falhas por classe ABC",
            "Peças utilizadas",
            "Peças por classe ABC",
        ],
    },
    "analise_tarefas": {
        "kpis": [
            "Total de tarefas", "Técnicos envolvidos", "Máquinas atendidas",
        ],
        "charts": [
            "Ritmo dos atendimentos",
            "Distribuição por responsável",
            "Concentração de tarefas por equipamento",
        ],
    },
    "maquinas": {
        "kpis": [
            "Total de tarefas", "% Corretivas",
            "Problema mais frequente", "Peça mais trocada",
        ],
        "charts": [
            "Histórico do equipamento",
            "Composição do equipamento",
        ],
    },
    "clientes_regioes": {
        "kpis": ["Total de tarefas", "Máquinas atendidas"],
        "charts": [],
    },
}


def apply_theme():
    st.markdown(
        """<style>
.block-container{max-width:1550px;padding-top:2rem;padding-bottom:3rem}

.kpi-card{
  background:linear-gradient(180deg,#FFFFFF 0%,#F8FAFC 100%);
  border:1px solid #E2E8F0;
  border-radius:14px;
  padding:16px 20px 14px 20px;
  box-shadow:0 1px 2px 0 rgba(0,0,0,0.04);
  margin-bottom:12px;
  transition:box-shadow .15s ease,transform .15s ease;
  min-height:170px;
  display:flex;
  flex-direction:column;
}
.kpi-card:hover{
  box-shadow:0 6px 16px -4px rgba(0,0,0,0.12);
  transform:translateY(-1px);
}
.kpi-border-primary{ border-left:5px solid #0284C7; }
.kpi-border-success{ border-left:5px solid #16A34A; }
.kpi-border-warning{ border-left:5px solid #F59E0B; }
.kpi-border-danger { border-left:5px solid #DC2626; }
.kpi-border-neutral{ border-left:5px solid #94A3B8; }

.kpi-header{
  display:flex;align-items:center;justify-content:space-between;
  gap:8px;margin-bottom:10px;
}
.kpi-label{
  font-size:11px;font-weight:700;color:#64748B;
  text-transform:uppercase;letter-spacing:.6px;
  line-height:1.35;cursor:help;
}

.kpi-value-row{
  display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
  margin-top:2px;
}
.kpi-value{
  font-size:32px;font-weight:800;color:#0F172A;
  line-height:1.05;letter-spacing:-0.8px;
}
.kpi-value-text{
  font-size:15px;font-weight:700;color:#0F172A;
  line-height:1.3;overflow-wrap:anywhere;
}

.kpi-delta{
  display:inline-flex;align-items:center;gap:2px;
  font-size:12px;font-weight:800;
  padding:3px 8px;border-radius:6px;
  white-space:nowrap;flex-shrink:0;
}
.kpi-delta-good{color:#15803D;background:#DCFCE7;}
.kpi-delta-bad {color:#B91C1C;background:#FEE2E2;}
.kpi-delta-flat{color:#64748B;background:#F1F5F9;font-weight:600;}

.kpi-sparkline{margin:4px 0 0 0;}

.kpi-progress{
  margin:14px 0 6px 0;height:6px;
  background:#F1F5F9;border-radius:3px;overflow:hidden;
}
.kpi-progress-fill{
  height:100%;border-radius:3px;
  transition:width .3s ease;
}

.kpi-footer{
  font-size:11px;color:#94A3B8;margin-top:auto;padding-top:8px;
  line-height:1.4;
}

.chips{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 16px 0}
.chip{background:#fff;border:1px solid #DCE4EC;border-radius:999px;
      padding:4px 12px;font-size:.78rem;color:#172B4D;white-space:nowrap}

.insights-title{font-size:1.05rem;font-weight:650;margin:8px 0 10px 0;color:#172B4D}
.insight-item{display:flex;gap:10px;padding:10px 14px;margin-bottom:6px;
              background:#fff;border-left:3px solid #245A81;
              border-radius:6px;font-size:.9rem;color:#172B4D}
.insight-num{font-weight:700;color:#245A81;min-width:18px}
</style>""",
        unsafe_allow_html=True,
    )


def widget(kind, label, key, **kwargs):
    saved = key + "_saved"
    if saved in st.session_state:
        value = st.session_state[saved]
        options = kwargs.get("options")
        if options is not None:
            if kind == "multiselect":
                value = [v for v in value if v in options]
            elif len(options) and value not in options:
                value = options[0]
        if kind == "number_input":
            if kwargs.get("min_value") is not None:
                value = max(kwargs["min_value"], value)
            if kwargs.get("max_value") is not None:
                value = min(kwargs["max_value"], value)
        st.session_state[key] = value
        kwargs.pop("default", None)
        kwargs.pop("value", None)

    def save():
        st.session_state[saved] = st.session_state[key]

    result = getattr(st, kind)(label, key=key, on_change=save, **kwargs)
    st.session_state[saved] = result
    return result


def norm_header(value):
    text = unicodedata.normalize("NFKD", str(value).strip().casefold())
    return " ".join(
        "".join(ch for ch in text if not unicodedata.combining(ch)).split()
    )


def _comparison_window_label(spec):
    period = spec.get("period")
    if not (isinstance(period, (tuple, list)) and len(period) == 2):
        return None
    try:
        start, end = map(pd.Timestamp, period)
    except Exception:
        return None
    duration = (end - start).days + 1
    if duration <= 0:
        return None
    prev_start = (start - pd.Timedelta(days=duration)).date()
    prev_end = (start - pd.Timedelta(days=1)).date()
    return prev_start, prev_end, duration


def _coverage_pct(prev_df, window):
    if prev_df is None or prev_df.empty or window is None:
        return 0.0
    _, _, duration = window
    if duration <= 0:
        return 0.0
    actual = (
        prev_df["Data da tarefa"].max()
        - prev_df["Data da tarefa"].min()
    ).days + 1
    return min(actual / duration, 1.0) * 100


def generate_insights(df, prev_df, spec):
    if df is None or df.empty:
        return []

    insights = []
    total = len(df)
    prev_total = len(prev_df) if prev_df is not None else 0

    if prev_total > 0:
        pct = (total - prev_total) / prev_total * 100
        if abs(pct) >= 10:
            verb = "aumentou" if pct > 0 else "reduziu"
            insights.append(
                f"Volume de tarefas {verb} {abs(pct):.0f}% vs período "
                f"anterior ({total} vs {prev_total})."
            )

    corr = int(df["Tipo"].eq("Corretiva").sum())
    if total:
        share = corr / total * 100
        if share >= 60:
            insights.append(
                f"Perfil predominantemente corretivo: {share:.0f}% das "
                "tarefas são corretivas — sinal de manutenção reativa."
            )
        elif share <= 30 and total >= 20:
            insights.append(
                f"Perfil preventivo saudável: apenas {share:.0f}% das "
                "tarefas são corretivas."
            )

    if "Rótulo da máquina" in df.columns:
        m = df.loc[
            df["Rótulo da máquina"].fillna("").astype(str).str.strip().ne(""),
            "Rótulo da máquina",
        ].value_counts()
        if len(m) >= 5 and total >= 20:
            top3 = m.head(3).sum() / total * 100
            if top3 >= 40:
                names = ", ".join(str(n) for n in m.head(3).index)
                insights.append(
                    f"Concentração em equipamentos: as 3 máquinas mais "
                    f"atendidas concentram {top3:.0f}% das tarefas ({names})."
                )

    if corr >= 5 and "Problema" in df.columns:
        probs = occurrence_frame(df, "Problema")["Problema"].value_counts()
        if len(probs):
            share = probs.iloc[0] / probs.sum() * 100
            if share >= 25:
                insights.append(
                    f'Falha dominante: "{probs.index[0]}" responde por '
                    f"{share:.0f}% das ocorrências corretivas."
                )

    if corr >= 5 and "Garantia" in df.columns:
        corr_df = df.loc[df["Tipo"].eq("Corretiva")]
        outside = int(corr_df["Garantia"].eq("Fora").sum())
        if len(corr_df) and outside / len(corr_df) >= 0.5:
            insights.append(
                f"{outside} corretivas fora da garantia — oportunidade de "
                "rever contrato de manutenção."
            )

    return insights[:5]


def render_insights(insights):
    if not insights:
        return
    st.markdown(
        '<div class="insights-title">O que os dados mostram</div>',
        unsafe_allow_html=True,
    )
    for i, text in enumerate(insights, 1):
        st.markdown(
            f'<div class="insight-item">'
            f'<span class="insight-num">{i}</span>{escape(text)}'
            f'</div>',
            unsafe_allow_html=True,
        )


def context(page_id, title, subtitle, corrective=False):
    st.title(title)
    st.caption(subtitle)

    ctx = st.session_state.get("_page_context")
    if ctx is None:
        st.error("Abra o aplicativo pelo app.py.")
        return None

    if not ctx["valid"]:
        st.info("Selecione um período válido na barra lateral.")
        return None

    data = ctx["cut"].copy()
    if corrective:
        data = data.loc[data["Tipo"].eq("Corretiva")].copy()

    if data.empty and page_id != "maquinas":
        st.info("Nenhum registro encontrado neste recorte.")
        return None

    spec = ctx["spec"]
    start, end = spec["period"]
    period_label = f"{start:%d/%m/%Y} a {end:%d/%m/%Y}"

    prev = previous_period(ctx["raw"], spec)
    if corrective:
        prev = prev.loc[prev["Tipo"].eq("Corretiva")]

    effective_spec = dict(spec)
    if corrective:
        effective_spec["Tipo"] = "Corretiva"

    labels = dict(
        zip(ctx["raw"]["Máquina"], ctx["raw"]["Seleção da máquina"])
    )
    filter_chips = []
    if spec.get("Tipo") and spec["Tipo"] != "Todas":
        filter_chips.append(spec["Tipo"])
    for col in COLUMNS:
        selected = spec.get(col)
        if not selected:
            continue
        text = ", ".join(
            str(labels.get(v, v)) if col == "Máquina" else str(v)
            for v in selected
        )
        filter_chips.append(f"{col}: {text}")

    loaded = st.session_state.get("_data_loaded_at")
    refreshed = loaded.strftime("%H:%M") if loaded else "—"
    chip_list = [
        f'<span class="chip">{escape(period_label)}</span>',
        f'<span class="chip">{len(data)} tarefas</span>',
        f'<span class="chip">Atualizado {refreshed}</span>',
    ] + [f'<span class="chip">{escape(x)}</span>' for x in filter_chips]
    st.markdown(
        f'<div class="chips">{"".join(chip_list)}</div>',
        unsafe_allow_html=True,
    )

    if not ctx["additional"]:
        st.caption(
            "Visão ampla do período — refine na lateral para focar em "
            "máquina, técnico, cliente ou região."
        )

    render_insights(generate_insights(data, prev, spec))

    return dict(
        id=page_id,
        raw=ctx["raw"],
        spec=spec,
        effective_spec=effective_spec,
        df=data,
        prev=prev,
        figures={},
        associations={},
        key="dash_" + page_id + "_",
        period_label=period_label,
        filter_chips=filter_chips,
    )


def chart_key(c, name):
    return c["key"] + hashlib.sha1(name.encode()).hexdigest()[:10]


def registry(c, name, fig, kpis):
    if fig is None:
        st.info("Sem ocorrências válidas para esta análise.")
        return
    revise_bar_labels(fig)
    fig.update_xaxes(rangeslider=dict(visible=False))
    c["figures"][name] = fig
    c["associations"][name] = set(kpis)
    st.plotly_chart(
        fig, use_container_width=True,
        key=chart_key(c, "figure_" + name),
    )


def _render_comparison_legend(c, deltas, reasons):
    window = _comparison_window_label(c["spec"])
    if not window:
        return
    ps, pe, dur = window

    if deltas:
        st.caption(
            f"Δ = variação vs **{ps:%d/%m/%Y}** a **{pe:%d/%m/%Y}** "
            f"({dur} dias, mesma duração do recorte atual)."
        )
    else:
        st.caption(
            f"💡 Nenhum KPI tem base de comparação. Período anterior "
            f"esperado: **{ps:%d/%m/%Y}** a **{pe:%d/%m/%Y}** ({dur} dias). "
            f"Reduza a **data inicial** no filtro Período para habilitar o Δ."
        )

    if reasons:
        with st.expander("🔍 Diagnóstico do delta", expanded=False):
            period = c["spec"]["period"]
            start_atual, end_atual = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            prev_len = len(c["prev"]) if c.get("prev") is not None else 0
            st.markdown(
                f"- **Recorte atual:** {start_atual:%d/%m/%Y} → {end_atual:%d/%m/%Y}\n"
                f"- **Período anterior esperado:** {ps:%d/%m/%Y} → {pe:%d/%m/%Y} ({dur} dias)\n"
                f"- **Tarefas no período anterior:** {prev_len}\n"
                f"- **Motivos de ausência de Δ:** `{reasons}`\n"
                f"- **Deltas calculados para:** `{list(deltas.keys())}`"
            )

    coverage = _coverage_pct(c.get("prev"), window)
    if deltas and coverage < 70:
        st.caption(
            f"⚠️ O período anterior tem só ~{coverage:.0f}% de cobertura "
            f"({coverage:.0f}% dos {dur} dias). KPIs de contagem podem "
            f"ficar distorcidos. Percentuais (% preventivas e "
            f"% corretivas) não são afetados."
        )
