import csv
import io
import re
import unicodedata

import pandas as pd
import requests
import streamlit as st

BASE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub"
URL_ABA_MASTER = BASE + "?gid=1187149031&single=true&output=csv"
URL_ABA_DADOS = BASE + "?gid=152468513&single=true&output=csv"


def clean(value):
    return "" if value is None or pd.isna(value) else str(value).strip()


def norm(value):
    value = unicodedata.normalize("NFKD", clean(value).lower())
    return re.sub(r"\s+", " ", "".join(c for c in value if not unicodedata.combining(c)))


ALIASES = {
    "codigo ar verificado": "Máquina",
    "tecnico": "Técnico",
    "manutencao": "Tipo",
    "data": "Data da tarefa",
    "problemas relatados": "Problema",
    "problema": "Problema",
    "tarefa": "Tarefa",
    "pecas trocadas": "Peça",
    "peca": "Peça",
    "data garantia": "Data Garantia",
    "equipamento": "Equipamento",
    "tipo": "Tipo Equipamento",
    "cliente": "Cliente",
    "cidade": "Cidade",
    "estado": "Estado",
    "regiao": "Região",
    # Novos aliases para o Resumo mensal
    "codigo interno": "Código Interno",
    "ambiente pmoc": "Ambiente PMOC",
    "unidade": "Unidade",
    "ambiente": "Ambiente PMOC",
}


def parse_csv(text, sheet):
    rows = list(csv.reader(io.StringIO(text)))
    required = (
        {"codigo ar verificado", "tecnico", "manutencao"}
        if sheet == "Master"
        else {"codigo ar verificado", "equipamento", "tipo"}
    )
    header = next(
        (i for i, row in enumerate(rows) if required.issubset({norm(v) for v in row})),
        None,
    )
    if header is None:
        raise ValueError(
            f"{sheet}: cabeçalho esperado não encontrado. "
            "Não serão puladas linhas silenciosamente."
        )
    names = [ALIASES.get(norm(v), clean(v)) for v in rows[header]]
    positions = [i for i, name in enumerate(names) if name]
    names = [names[i] for i in positions]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(
            f"{sheet}: colunas repetidas após normalização: {duplicates}"
        )
    records = [
        [row[i] if i < len(row) else "" for i in positions]
        for row in rows[header + 1:]
    ]
    return pd.DataFrame(records, columns=names)


def read_sheet(url, sheet):
    response = requests.get(url, timeout=40)
    response.raise_for_status()
    try:
        text = response.content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"{sheet}: exportação não está em UTF-8; confira a publicação CSV."
        ) from error
    if "<html" in text[:500].lower() or "<!doctype" in text[:500].lower():
        raise ValueError(f"{sheet}: o endereço retornou HTML em vez de CSV.")
    return parse_csv(text, sheet)


def normalize_tables(master, machines):
    """
    Visão das páginas analíticas — parte da Master (tarefas).
    Máquinas sem tarefa NÃO aparecem. Mantida intacta para não
    afetar Visão geral, Corretivas, Operação, Equipamentos, Clientes.
    """
    required = {"Máquina", "Tipo", "Data da tarefa", "Técnico"}
    missing = required - set(master.columns)
    if missing:
        raise ValueError(f"Master: faltam colunas obrigatórias: {sorted(missing)}")
    master = master.copy()
    machines = machines.copy()
    for frame in (master, machines):
        for column in frame.columns:
            frame[column] = frame[column].map(clean)
    master = master.loc[master["Máquina"].ne("")].copy()
    machines = machines.loc[machines["Máquina"].ne("")].copy()
    if machines["Máquina"].duplicated().any():
        codes = machines.loc[machines["Máquina"].duplicated(False), "Máquina"].unique()
        raise ValueError("Dados: códigos de máquina repetidos: " + ", ".join(codes[:10]))
    enrich = [c for c in machines.columns if c == "Máquina" or c not in master.columns]
    df = master.merge(machines[enrich], on="Máquina", how="left", validate="many_to_one")
    df["Tipo"] = df["Tipo"].map(
        lambda v: {"preventiva": "Preventiva", "corretiva": "Corretiva"}.get(norm(v), clean(v))
    )
    for column in [
        "Equipamento", "Tipo Equipamento", "Cliente", "Cidade", "Estado", "Região",
        "Problema", "Peça", "Tarefa", "Código Interno", "Ambiente PMOC", "Unidade",
    ]:
        if column not in df:
            df[column] = ""
        df[column] = df[column].map(clean)
    for column in ["Data da tarefa", "Data Garantia"]:
        if column not in df:
            df[column] = ""
        df[column] = pd.to_datetime(df[column], format="mixed", dayfirst=True, errors="coerce")
    df["Nome da máquina"] = df["Equipamento"].where(df["Equipamento"].ne(""), df["Máquina"])
    repeated_names = df.groupby("Nome da máquina")["Máquina"].transform("nunique").gt(1)
    df["Rótulo da máquina"] = df["Nome da máquina"].where(
        ~repeated_names, df["Nome da máquina"] + " — " + df["Máquina"]
    )
    df["Seleção da máquina"] = df["Nome da máquina"] + " — " + df["Máquina"]
    df["Garantia"] = ""
    corr = df["Tipo"].eq("Corretiva")
    df.loc[corr, "Garantia"] = "Não informado"
    known = corr & df["Data Garantia"].notna()
    today = pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None).normalize()
    df.loc[known & df["Data Garantia"].ge(today), "Garantia"] = "Dentro"
    df.loc[known & df["Data Garantia"].lt(today), "Garantia"] = "Fora"
    return df.reset_index(drop=True)


def normalize_registry(machines):
    """
    Cadastro de máquinas como base independente — parte de Dados.

    Preserva TODAS as máquinas, inclusive as que nunca tiveram
    tarefa. É a base do Resumo mensal, que inverte a lógica das
    páginas analíticas (lá Master é base, aqui Dados é base).
    """
    machines = machines.copy()
    for column in machines.columns:
        machines[column] = machines[column].map(clean)
    machines = machines.loc[machines["Máquina"].ne("")].copy()
    if machines["Máquina"].duplicated().any():
        codes = machines.loc[machines["Máquina"].duplicated(False), "Máquina"].unique()
        raise ValueError("Dados: códigos de máquina repetidos: " + ", ".join(codes[:10]))

    for column in [
        "Equipamento", "Tipo Equipamento", "Cliente", "Cidade", "Estado", "Região",
        "Código Interno", "Ambiente PMOC", "Unidade",
    ]:
        if column not in machines.columns:
            machines[column] = ""
        machines[column] = machines[column].map(clean)

    # Identificação principal: Código Interno, com fallback para Nome ou código
    ident = machines["Código Interno"].where(machines["Código Interno"].ne(""), "")
    ident = ident.where(ident.ne(""), machines["Equipamento"])
    ident = ident.where(ident.ne(""), machines["Máquina"])
    machines["Identificação"] = ident

    # Desambiguação se o Código Interno repetir dentro do cadastro
    dup = machines["Identificação"].duplicated(keep=False) & machines["Identificação"].ne("")
    machines.loc[dup, "Identificação"] = (
        machines.loc[dup, "Identificação"]
        + " ("
        + machines.loc[dup, "Máquina"]
        + ")"
    )

    return machines.reset_index(drop=True)


@st.cache_data(ttl=60)
def load_all():
    """Retorna (tarefas, cadastro_de_máquinas). Uma leitura por cache."""
    master = read_sheet(URL_ABA_MASTER, "Master")
    machines = read_sheet(URL_ABA_DADOS, "Dados")
    tasks = normalize_tables(master.copy(), machines.copy())
    registry = normalize_registry(machines.copy())
    return tasks, registry


def load_and_normalize_data():
    """Compatibilidade com as páginas analíticas — retorna só as tarefas."""
    tasks, _ = load_all()
    return tasks
