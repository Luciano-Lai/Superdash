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

def configuration(c, kpi_options, chart_options):
    values, deltas, previous, reasons = calculate_kpis_with_delta(
        c["df"], c.get("prev")
    )
    series = compute_kpi_series(
        c["raw"],
        c.get("effective_spec") or c["spec"],
    )
    available_kpis = [k for k in kpi_options if k in values]
    kpi_saved = c["key"] + "kpis_saved"
    chart_saved = c["key"] + "analyses_saved"
    preset = EXECUTIVE_PRESETS.get(c["id"], {})

    if kpi_saved not in st.session_state:
        st.session_state[kpi_saved] = [
            k for k in preset.get("kpis", []) if k in available_kpis
        ]
    if chart_saved not in st.session_state:
        st.session_state[chart_saved] = [
            k for k in preset.get("charts", []) if k in chart_options
        ]

    with st.expander("⚙️  Indicadores, análises e PDF", expanded=True):
        col_a, col_b = st.columns([1, 5])
        if col_a.button(
            "↩ Restaurar",
            key=c["key"] + "reset",
            help="Volta à visão inicial desta página",
            use_container_width=True,
        ):
            st.session_state[kpi_saved] = [
                k for k in preset.get("kpis", []) if k in available_kpis
            ]
            st.session_state[chart_saved] = [
                k for k in preset.get("charts", []) if k in chart_options
            ]
            st.toast("Visão inicial restaurada.", icon="↩")

        left, right = st.columns(2)
        if left.button(
            "Selecionar todos os indicadores",
            key=c["key"] + "all_kpis",
        ):
            st.session_state[kpi_saved] = list(available_kpis)
            st.toast("Todos os indicadores foram selecionados.", icon="✅")
        if right.button(
            "Limpar indicadores",
            key=c["key"] + "none_kpis",
        ):
            st.session_state[kpi_saved] = []
            st.toast("Indicadores limpos.", icon="🧹")

        selected_kpis = widget(
            "multiselect",
            "Indicadores desta página",
            c["key"] + "kpis",
            options=available_kpis,
            default=[],
        )

        left, right = st.columns(2)
        if left.button(
            "Selecionar todas as análises",
            key=c["key"] + "all",
            disabled=not selected_kpis,
        ):
            st.session_state[chart_saved] = list(chart_options)
            st.toast("Todas as análises foram selecionadas.", icon="✅")
        if right.button(
            "Limpar análises",
            key=c["key"] + "none",
        ):
            st.session_state[chart_saved] = []
            st.toast("Análises limpas.", icon="🧹")

        selected = widget(
            "multiselect",
            "Análises desta página",
            c["key"] + "analyses",
            options=chart_options,
            default=[],
            disabled=not selected_kpis,
        )

        top = widget(
            "number_input",
            "Nível de detalhe (Top N)",
            "dash_global_top",
            min_value=1,
            value=10,
            step=1,
            help="Quantidade de categorias exibidas nos rankings e roscas.",
        )

        export_slot = st.container()

    c.update(
        values=values,
        deltas=deltas,
        previous=previous,
        reasons=reasons,
        series=series,
        kpis=selected_kpis,
        selected=selected if selected_kpis else [],
        top=int(top),
        export_slot=export_slot,
    )

    if selected_kpis:
        st.subheader("Indicadores do recorte")
        render_kpi_cards(
            selected_kpis, values,
            deltas=deltas, series=series, previous=previous,
            reasons=reasons,
        )
        _render_comparison_legend(c, deltas, reasons)
    else:
        st.info(
            "Selecione indicadores para habilitar as análises desta página."
        )

    return c


def evolution(c, name="Evolução no período"):
    key = chart_key(c, name)
    prev_available = c.get("prev") is not None and not c["prev"].empty

    left, mid, right = st.columns(3)
    with left:
        gran = widget(
            "selectbox", "Agrupamento", key + "gran",
            options=["Diária", "Semanal", "Mensal"],
        )
    with mid:
        visual = widget(
            "selectbox", "Visual", key + "visual",
            options=["Barras", "Linha", "Barras + linha acumulada"],
        )
    with right:
        if prev_available:
            compare = widget(
                "checkbox",
                "Comparar com período anterior",
                key + "cmp",
                value=True,
                help=(
                    "Sobreponha o período anterior (mesma duração) como "
                    "linha tracejada cinza. Este controle afeta apenas "
                    "este gráfico — os cards de KPI calculam o delta "
                    "independentemente."
                ),
            )
        else:
            compare = False
            st.markdown("**Comparação**")
            st.caption("sem período anterior")

    prev = c.get("prev") if compare and prev_available else None
    fig = render_evolution_chart(
        c["df"], gran, visual, c["spec"]["period"], prev,
    )
    registry(
        c, name, fig,
        {
            "Total de tarefas", "Preventivas", "Corretivas",
            "% Preventivas", "% Corretivas",
        },
    )
    if not prev_available:
        st.caption(
            "💡 Para comparar com um período anterior, reduza a "
            "**data inicial** no filtro Período da lateral."
        )


def ranking(c, column, title, associated, kind=None):
    source = c["df"]
    if kind:
        source = source.loc[source["Tipo"].eq(kind)]
    if source.empty or column not in source.columns:
        st.info("Não há registros para " + title.lower() + ".")
        return
    counts = category_counts(source, column)
    if counts.empty:
        st.info("Não há ocorrências válidas para " + title.lower() + ".")
        return
    key = chart_key(c, title)
    st.markdown("### " + title)
    with st.expander("Ajustes — " + title):
        own = widget(
            "checkbox", "Definir Top N individual",
            key + "override", value=False,
        )
        n = int(
            widget(
                "number_input", "Top N individual", key + "n",
                min_value=1, max_value=len(counts),
                value=min(10, len(counts)), step=1,
            )
            if own else c["top"]
        )
        pair = widget(
            "checkbox", "Mostrar distribuição do recorte",
            key + "pair", value=False,
        )
        others = widget(
            "checkbox", "Agrupar restante em Outras",
            key + "others", value=True,
        )
    bars = render_horizontal_ranking(source, column, title, n)
    st.caption(
        f"{len(counts)} categorias no recorte • "
        f"{min(n, len(counts))} exibidas no ranking"
    )
    if not pair:
        registry(c, title, bars, associated)
        return
    donut_title = title + " — distribuição no recorte"
    donut = render_donut_chart(source, column, donut_title, n, others)
    entries = min(n, len(counts)) + int(others and len(counts) > n)
    if entries <= 10:
        left, right = st.columns([1.1, 1])
        with left:
            registry(c, title, bars, associated)
        with right:
            registry(c, donut_title, donut, associated)
    else:
        registry(c, title, bars, associated)
        st.markdown("#### Distribuição do recorte")
        st.caption(
            f"{entries} entradas na rosca. A distribuição ocupa uma "
            "área própria."
        )
        registry(c, donut_title, donut, associated)
    if not others and len(counts) > n:
        st.caption(
            "Sem “Outras”, os percentuais da rosca consideram somente "
            "as categorias exibidas."
        )


def composition(c, title):
    registry(
        c, title,
        render_donut_chart(c["df"], "Tipo", title, 10, True),
        {
            "Total de tarefas", "Preventivas", "Corretivas",
            "% Preventivas", "% Corretivas",
        },
    )


def _category_rows(df, column, members):
    if column in {"Problema", "Peça"}:
        occurrences = occurrence_frame(df, column)
        indexes = occurrences.loc[
            occurrences[column].isin(members)
        ].index.unique()
        return df.loc[df.index.isin(indexes)].copy()
    values = df[column].fillna("").astype(str).str.strip()
    return df.loc[values.isin(members)].copy()


def concentration(c, column, title, associated, kind=None, drilldown=()):
    source = c["df"]
    if kind:
        source = source.loc[source["Tipo"].eq(kind)]
    if source.empty or column not in source.columns:
        st.info("Não há registros para " + title.lower() + ".")
        return
    key = chart_key(c, title)
    st.markdown("### " + title)

    analysis = source.copy()
    counts = category_counts(analysis, column)
    if counts.empty:
        st.info("Não há categorias válidas para esta análise.")
        return

    with st.expander(
        "Ajustes do Pareto principal — " + title, expanded=True
    ):
        all_items = widget(
            "checkbox", "Exibir todas as categorias no Pareto principal",
            key + "show_all", value=False,
        )
        n = widget(
            "number_input", "Top N do Pareto principal",
            key + "principal_top", min_value=1, max_value=len(counts),
            value=min(c["top"], len(counts)), step=1,
            disabled=all_items,
        )
        left, right = st.columns(2)
        a_percent = left.number_input(
            "Limite da classe A (%)",
            min_value=1, max_value=98, value=80, step=1,
            key=key + "a",
        )
        b_percent = right.number_input(
            "Limite da classe B (%)",
            min_value=2, max_value=100, value=95, step=1,
            key=key + "b",
        )

    if b_percent <= a_percent:
        st.warning("O limite da classe B deve ser maior que o da A.")
        return

    a, b = a_percent / 100, b_percent / 100
    abc = abc_table(counts, a, b)
    unit = (
        "ocorrências" if column in {"Problema", "Peça"} else "tarefas"
    )
    total = int(abc["Quantidade"].sum())
    top_n = None if all_items else int(n)
    registry(
        c, title,
        render_pareto_chart(counts, title, top_n, None, a, b, unit),
        associated,
    )
    shown = abc if top_n is None else abc.head(top_n)
    shown_total = int(shown["Quantidade"].sum())
    st.caption(
        f"Exibindo {len(shown)} de {len(abc)} categorias — "
        f"{shown_total / total * 100:.2f}% do volume "
        f"({total} {unit} na base). O Top N não altera a ABC."
    )

    st.markdown("#### Composição da Curva ABC")
    registry(
        c, title + " — classes",
        render_abc_donut(abc, title + " — classes A, B e C", unit),
        associated,
    )
    summary = (
        abc.groupby("Classe")
        .agg(
            Categorias=("Categoria", "nunique"),
            Volume=("Quantidade", "sum"),
        )
        .reindex(["A", "B", "C"])
        .fillna(0)
    )
    for slot, letter in zip(st.columns(3), ["A", "B", "C"]):
        volume = int(summary.loc[letter, "Volume"])
        items = int(summary.loc[letter, "Categorias"])
        slot.metric(
            "Classe " + letter,
            f"{volume:,}".replace(",", "."),
            f"{items} categoria(s) • {volume / total * 100:.2f}%",
            delta_color="off",
        )

    with st.expander("Tabela de classificação ABC"):
        display_abc = abc.rename(
            columns={
                "Participação": "Participação (%)",
                "Acumulado %": "Acumulado (%)",
            }
        ).copy()
        for col in ["Participação (%)", "Acumulado (%)"]:
            display_abc[col] = display_abc[col].round(2)
        st.dataframe(
            display_abc, hide_index=True, use_container_width=True,
            column_config={
                "Categoria": st.column_config.TextColumn(
                    "Categoria", width="large"
                ),
                "Quantidade": st.column_config.NumberColumn(
                    "Quantidade", format="%d"
                ),
                "Participação (%)": st.column_config.NumberColumn(
                    "Participação (%)", format="%.2f"
                ),
                "Acumulado": st.column_config.NumberColumn(
                    "Acumulado", format="%d"
                ),
                "Acumulado (%)": st.column_config.NumberColumn(
                    "Acumulado (%)", format="%.2f"
                ),
                "Classe": st.column_config.TextColumn("Classe"),
            },
        )

    available = [
        letter for letter in ["A", "B", "C"]
        if summary.loc[letter, "Categorias"] > 0
    ]
    if not drilldown or not available:
        return

    st.markdown("#### Detalhar uma classe")
    selected = widget(
        "selectbox", "Classe para detalhar", key + "class",
        options=available,
        format_func=lambda letter: "Classe " + letter,
    )
    members = abc.loc[abc["Classe"].eq(selected), "Categoria"].tolist()
    subset = _category_rows(analysis, column, members)
    options = [item for item in drilldown if item in subset.columns]
    if subset.empty or not options:
        st.info("Sem registros válidos para o detalhamento.")
        return
    st.caption(
        f"Classe {selected}: {len(members)} categorias • "
        f"{len(subset)} tarefas relacionadas."
    )
    breakdown = widget(
        "selectbox", "Analisar a classe por", key + "breakdown",
        options=options,
    )
    inner_counts = category_counts(subset, breakdown)
    if inner_counts.empty:
        st.info("Sem ocorrências válidas neste detalhamento.")
        return
    suffix = hashlib.sha1(
        (selected + "|" + breakdown).encode()
    ).hexdigest()[:12]
    inner_key = key + "_inner_" + suffix
    with st.expander(
        "Ajustes do Pareto interno — " + breakdown, expanded=True
    ):
        inner_all = widget(
            "checkbox", "Exibir todas as categorias neste detalhamento",
            inner_key + "all", value=False,
        )
        inner_n = widget(
            "number_input", "Top N deste detalhamento",
            inner_key + "top", min_value=1, max_value=len(inner_counts),
            value=min(c["top"], len(inner_counts)), step=1,
            disabled=inner_all,
        )
    inner_top_n = None if inner_all else int(inner_n)
    inner_unit = (
        "ocorrências" if breakdown in {"Problema", "Peça"} else "tarefas"
    )
    inner_title = title + f" — classe {selected} — {breakdown.lower()}"
    registry(
        c, inner_title,
        render_pareto_chart(
            inner_counts, inner_title, inner_top_n, None, a, b, inner_unit
        ),
        associated,
    )
    inner_shown = (
        inner_counts if inner_top_n is None
        else inner_counts.head(inner_top_n)
    )
    inner_total = int(inner_counts.sum())
    coverage = (
        float(inner_shown.sum()) / inner_total * 100 if inner_total else 0
    )
    st.caption(
        f"Exibindo {len(inner_shown)} de {len(inner_counts)} categorias "
        f"— {coverage:.2f}% do volume deste detalhamento "
        f"({inner_total} {inner_unit})."
    )
    st.caption(
        "O acumulado deste detalhamento usa somente o volume da classe "
        "selecionada. As cores indicam uma ABC interna, sem alterar a "
        "classificação original. Os controles internos são independentes "
        "dos controles principais."
    )


