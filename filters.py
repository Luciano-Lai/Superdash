import json
import unicodedata

import pandas as pd
import streamlit as st


COLUMNS = [
    "Máquina",
    "Técnico",
    "Cliente",
    "Estado",
    "Região",
    "Cidade",
]


def alphabetical_key(value):
    text = unicodedata.normalize("NFKD", str(value).strip().casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


def reset_dashboard():
    for key in list(st.session_state):
        if key.startswith("dash_"):
            del st.session_state[key]
    st.session_state.pop("_url_imported", None)


def apply_filters(df, spec, ignore=()):
    result = df.copy()
    period = spec.get("period", ())
    if len(period) != 2:
        return result.iloc[0:0].copy()
    start, end = map(pd.Timestamp, period)
    result = result.loc[
        result["Data da tarefa"].ge(start)
        & result["Data da tarefa"].lt(end + pd.Timedelta(days=1))
    ]
    selected_type = spec.get("Tipo", "Todas")
    if "Tipo" not in ignore and selected_type != "Todas":
        result = result.loc[result["Tipo"].eq(selected_type)]
    for column in COLUMNS:
        if column in ignore:
            continue
        selected = spec.get(column)
        if selected:
            result = result.loc[result[column].isin(selected)]
    return result.copy()


def previous_period(df, spec):
    """Mesmo recorte, janela anterior de igual duração (imediatamente antes)."""
    period = spec.get("period", ())
    if not (isinstance(period, (tuple, list)) and len(period) == 2):
        return df.iloc[0:0].copy()
    try:
        start, end = map(pd.Timestamp, period)
    except Exception:
        return df.iloc[0:0].copy()
    duration = (end - start).days + 1
    prev_spec = {
        **spec,
        "period": (
            (start - pd.Timedelta(days=duration)).date(),
            (start - pd.Timedelta(days=1)).date(),
        ),
    }
    return apply_filters(df, prev_spec)


def import_state_from_url(df):
    """Primeira execução: lê filtros da URL, se existirem e forem válidos."""
    if st.session_state.get("_url_imported"):
        return
    st.session_state["_url_imported"] = True
    raw = st.query_params.get("f")
    if not raw:
        return
    try:
        payload = json.loads(raw)
    except Exception:
        return

    valid = df["Data da tarefa"].dropna()
    if "p" in payload and isinstance(payload["p"], list) and len(payload["p"]) == 2 and not valid.empty:
        try:
            start = pd.Timestamp(payload["p"][0]).date()
            end = pd.Timestamp(payload["p"][1]).date()
            lo, hi = valid.min().date(), valid.max().date()
            start = max(lo, min(hi, start))
            end = max(lo, min(hi, end))
            if start <= end:
                st.session_state["dash_period"] = (start, end)
        except Exception:
            pass

    if payload.get("t") in ("Todas", "Preventiva", "Corretiva"):
        st.session_state["dash_type"] = payload["t"]

    for col in COLUMNS:
        if col in payload and isinstance(payload[col], list):
            st.session_state[f"dash_filter_{col}"] = payload[col]


def export_state_to_url(spec):
    if not spec or "period" not in spec:
        return
    period = spec.get("period")
    if not (isinstance(period, (tuple, list)) and len(period) == 2):
        return
    payload = {
        "p": [pd.Timestamp(p).strftime("%Y-%m-%d") for p in period],
        "t": spec.get("Tipo"),
    }
    for col in COLUMNS:
        v = spec.get(col)
        if v:
            payload[col] = list(v)
    st.query_params["f"] = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def render_sidebar_filters(df):
    with st.sidebar:
        st.header("Filtros")
        st.caption("Escolha **o que** analisar. O período vem por último.")

        spec = {}

        # 1. Tipo primeiro
        spec["Tipo"] = st.selectbox(
            "Tipo de manutenção",
            ["Todas", "Preventiva", "Corretiva"],
            key="dash_type",
        )

        # 2. Dimensões
        labels = dict(zip(df["Máquina"], df["Seleção da máquina"]))
        for column in COLUMNS:
            options = [
                v for v in df[column].dropna().unique() if str(v).strip()
            ]
            if column == "Máquina":
                options = sorted(
                    options,
                    key=lambda code: (
                        alphabetical_key(labels.get(code, code)),
                        alphabetical_key(code),
                    ),
                )
            else:
                options = sorted(options, key=alphabetical_key)

            if not options:
                spec[column] = []
                st.caption(f"{column}: sem cadastro na fonte.")
                continue

            kwargs = {}
            if column == "Máquina":
                kwargs["format_func"] = lambda code: labels.get(code, code)

            spec[column] = st.multiselect(
                column,
                options,
                key=f"dash_filter_{column}",
                **kwargs,
            )

        # 3. Período por último
        st.divider()
        valid_dates = df["Data da tarefa"].dropna()
        if valid_dates.empty:
            st.error("Não há datas válidas na base.")
            return df.iloc[0:0].copy(), False, False, {}

        period = st.date_input(
            "Período",
            value=(valid_dates.min().date(), valid_dates.max().date()),
            min_value=valid_dates.min().date(),
            max_value=valid_dates.max().date(),
            format="DD/MM/YYYY",
            key="dash_period",
        )
        spec["period"] = period

        # 4. Ações
        st.divider()
        cols = st.columns(2)
        cols[0].button(
            "🧹 Limpar", on_click=reset_dashboard, use_container_width=True
        )
        if cols[1].button("🔄 Atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    valid_period = (
        isinstance(period, (tuple, list))
        and len(period) == 2
        and period[0] <= period[1]
    )
    additional = spec["Tipo"] != "Todas" or any(
        spec.get(c) for c in COLUMNS
    )
    cut = apply_filters(df, spec) if valid_period else df.iloc[0:0].copy()
    return cut, valid_period, additional, spec
