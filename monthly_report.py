from datetime import date
from html import escape

import pandas as pd
import streamlit as st

from data_loader import load_all
from monthly_pdf import generate_monthly_pdf


MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def month_bounds(year, month):
    primeiro = date(year, month, 1)
    prox = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    ultimo = prox - pd.Timedelta(days=1)
    hoje = date.today()
    if (year, month) == (hoje.year, hoje.month):
        return primeiro, min(hoje, ultimo), True
    return primeiro, ultimo, False


def build_monthly_report(registry, tasks, client, year, month, ambiente=None):
    start, end, parcial = month_bounds(year, month)

    machines = registry.copy()
    if client:
        machines = machines[machines["Cliente"].eq(client)].copy()
    if ambiente:
        machines = machines[machines["Ambiente PMOC"].eq(ambiente)].copy()

    if tasks.empty:
        period_tasks = tasks.copy()
    else:
        period_tasks = tasks[
            tasks["Data da tarefa"].notna()
            & tasks["Data da tarefa"].dt.date.between(start, end)
        ].copy()

    # ---------- Preventivas ----------
    prev = period_tasks[period_tasks["Tipo"].eq("Preventiva")].copy()
    if prev.empty:
        last_prev = pd.DataFrame(
            columns=["Máquina", "Última preventiva", "Técnicos"]
        )
    else:
        agg = (
            prev.sort_values("Data da tarefa", ascending=False)
            .groupby("Máquina")
            .agg(ultima_data=("Data da tarefa", "max"))
            .reset_index()
        )
        rows_ultima = prev.merge(agg, on="Máquina", how="inner")
        rows_ultima = rows_ultima[
            rows_ultima["Data da tarefa"].eq(rows_ultima["ultima_data"])
        ]
        tecnicos = (
            rows_ultima.groupby("Máquina")["Técnico"]
            .agg(lambda s: " / ".join(sorted({t for t in s if t})))
            .reset_index()
            .rename(columns={"Técnico": "Técnicos"})
        )
        last_prev = agg.rename(columns={"ultima_data": "Última preventiva"})
        last_prev = last_prev.merge(tecnicos, on="Máquina", how="left")

    preventivas = machines.merge(last_prev, on="Máquina", how="left")
    preventivas = preventivas.sort_values(
        "Identificação",
        key=lambda s: s.str.normalize("NFKD").str.casefold(),
    ).reset_index(drop=True)

    # ---------- Corretivas ----------
    corr = period_tasks[period_tasks["Tipo"].eq("Corretiva")].copy()
    if not corr.empty:
        corr = corr.merge(
            machines[["Máquina", "Identificação", "Ambiente PMOC"]],
            on="Máquina",
            how="left",
        )
        corr["Identificação"] = corr["Identificação"].fillna(corr["Máquina"])

    return {
        "preventivas": preventivas,
        "corretivas": corr,
        "parcial": parcial,
        "periodo": (start, end),
        "client": client,
        "year": year,
        "month": month,
        "ambiente": ambiente,
        "machines": machines,
    }


def render_preventivas(df):
    if df.empty:
        st.info("Nenhuma máquina no cadastro para o filtro selecionado.")
        return

    display = df.copy()
    display["Última preventiva no mês"] = display["Última preventiva"].apply(
        lambda d: f"{d:%d/%m/%Y}" if pd.notna(d) else "—"
    )
    display["Técnico(s)"] = display["Técnicos"].fillna("—")
    display["Situação"] = display["Última preventiva no mês"].apply(
        lambda v: "Sem registro de manutenção preventiva neste mês."
        if v == "—"
        else ""
    )

    main = display[[
        "Identificação", "Ambiente PMOC",
        "Última preventiva no mês", "Técnico(s)", "Situação",
    ]].rename(columns={"Identificação": "Código interno"})

    st.dataframe(
        main,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Código interno": st.column_config.TextColumn(width="medium"),
            "Ambiente PMOC": st.column_config.TextColumn(width="medium"),
            "Última preventiva no mês": st.column_config.TextColumn(width="small"),
            "Técnico(s)": st.column_config.TextColumn(width="medium"),
            "Situação": st.column_config.TextColumn(width="large"),
        },
    )

    with st.expander("Informações cadastrais", expanded=False):
        detail = display[[
            "Identificação", "Equipamento", "Máquina",
            "Tipo Equipamento", "Unidade",
        ]].rename(columns={
            "Identificação": "Código interno",
            "Equipamento": "Nome cadastrado",
            "Máquina": "Código AR Verificado",
            "Tipo Equipamento": "Tipo",
        })
        st.dataframe(detail, hide_index=True, use_container_width=True)


def render_corretivas(df):
    if df.empty:
        st.info(
            "Nenhum atendimento corretivo registrado no mês até a "
            "data de referência."
        )
        return

    st.caption(
        f"{len(df)} atendimento(s) em "
        f"{df['Identificação'].nunique()} máquina(s)."
    )

    recent = (
        df.groupby("Identificação")["Data da tarefa"].max()
        .sort_values(ascending=False)
    )

    for ident in recent.index:
        group = df[df["Identificação"].eq(ident)].copy()
        group = group.sort_values("Data da tarefa", ascending=False)
        row0 = group.iloc[0]

        st.markdown(f"### {escape(str(ident))}")
        env = row0.get("Ambiente PMOC") or "—"
        codigo_ar = row0["Máquina"]
        st.caption(
            f"Ambiente PMOC: {env} • Código do sistema: {codigo_ar} • "
            f"Atendimentos no mês: {len(group)}"
        )

        display = group[[
            "Data da tarefa", "Problema", "Tarefa", "Peça", "Técnico",
        ]].rename(columns={
            "Data da tarefa": "Data",
            "Problema": "Problema relatado",
            "Tarefa": "Tarefa executada",
            "Peça": "Peça trocada",
            "Técnico": "Técnico",
        })
        display["Data"] = display["Data"].apply(
            lambda d: f"{d:%d/%m/%Y}" if pd.notna(d) else "—"
        )
        for col in ["Problema relatado", "Tarefa executada", "Peça trocada", "Técnico"]:
            display[col] = display[col].fillna("—")

        st.dataframe(display, hide_index=True, use_container_width=True)
        st.divider()


def _pick_client(registry):
    """
    Escolhe o cliente conforme o cadastro atual:
      - 0 clientes distintos → None (bloqueio removido, todos)
      - 1 cliente           → usa o valor, sem selectbox
      - 2+ clientes         → selectbox com 'Todos os clientes' como default
    """
    clientes = sorted({c for c in registry["Cliente"].tolist() if c})
    if not clientes:
        st.caption(
            "Cliente: não cadastrado na base atual. "
            "O relatório considera todas as máquinas do cadastro."
        )
        return None
    if len(clientes) == 1:
        st.caption(f"Cliente: **{clientes[0]}**")
        return clientes[0]

    opcoes = ["Todos os clientes"] + clientes
    escolha = st.selectbox("Cliente", opcoes, key="resumo_cliente")
    return None if escolha == "Todos os clientes" else escolha


def _pick_ambiente(registry, client):
    """Mesma lógica do cliente, aplicada ao Ambiente PMOC."""
    base = registry.copy()
    if client:
        base = base[base["Cliente"].eq(client)]
    ambientes = sorted({a for a in base["Ambiente PMOC"].tolist() if a})

    if not ambientes:
        return None
    if len(ambientes) == 1:
        return ambientes[0]

    opcoes = ["Todos os ambientes"] + ambientes
    escolha = st.selectbox(
        "Unidade ou ambiente", opcoes, key="resumo_ambiente",
    )
    return None if escolha == "Todos os ambientes" else escolha


def render_resumo_mensal():
    st.title("Resumo mensal")
    st.caption(
        "Relatório por competência a partir do cadastro de máquinas. "
        "Não utiliza os filtros da lateral."
    )

    try:
        tasks, registry = load_all()
    except Exception as error:
        st.error(f"Falha ao carregar dados: {error}")
        return

    if registry.empty:
        st.info("O cadastro de máquinas (Dados) está vazio.")
        return

    hoje = date.today()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        cliente = _pick_client(registry)
    with col2:
        mes_nome = st.selectbox(
            "Mês", MESES, index=hoje.month - 1, key="resumo_mes",
        )
        mes = MESES.index(mes_nome) + 1
    with col3:
        anos = sorted({hoje.year - 1, hoje.year}, reverse=True)
        ano = st.selectbox("Ano", anos, key="resumo_ano")

    ambiente = _pick_ambiente(registry, cliente)

    report = build_monthly_report(
        registry, tasks, cliente, ano, mes, ambiente,
    )

    if report["machines"].empty:
        st.warning("Nenhuma máquina cadastrada com esse filtro.")
        return

    start, end = report["periodo"]
    titulo = f"**{mes_nome}/{ano}**"
    if cliente:
        titulo = f"**{cliente}** — {mes_nome}/{ano}"
    if ambiente:
        titulo += f" — {ambiente}"
    st.markdown(titulo)

    chips = [
        f'<span class="chip">Competência: {mes_nome}/{ano}</span>',
        f'<span class="chip">Período: {start:%d/%m/%Y} a {end:%d/%m/%Y}</span>',
        f'<span class="chip">Situação: '
        f'{"Parcial — mês em andamento" if report["parcial"] else "Mês completo"}'
        f'</span>',
        f'<span class="chip">Máquinas no cadastro: {len(report["machines"])}</span>',
        f'<span class="chip">Emissão: {date.today():%d/%m/%Y}</span>',
    ]
    st.markdown(
        f'<div class="chips">{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Relação de máquinas conforme o cadastro atual. "
        "Manutenções referentes à competência selecionada."
    )

    st.subheader(f"Preventivas no mês — {len(report['preventivas'])} máquinas")
    render_preventivas(report["preventivas"])

    st.subheader("Corretivas no mês")
    render_corretivas(report["corretivas"])

    st.divider()
    if st.button("Gerar PDF do resumo mensal", key="resumo_pdf_btn"):
        try:
            pdf = generate_monthly_pdf(report)
            sufixo = f"{ano}_{mes:02d}"
            if cliente:
                sufixo = cliente + "_" + sufixo
            st.download_button(
                "Baixar PDF",
                pdf,
                f"resumo_{sufixo}.pdf".replace(" ", "_"),
                "application/pdf",
                key="resumo_pdf_download",
            )
        except Exception as error:
            st.error("Não foi possível gerar o PDF.")
            st.code(str(error))
