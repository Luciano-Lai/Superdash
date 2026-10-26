import concurrent.futures
import csv
import io
import re
import time
import unicodedata

import pandas as pd
import requests
import streamlit as st

BASE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub"
URL_ABA_MASTER = BASE + "?gid=1187149031&single=true&output=csv"
URL_ABA_DADOS = BASE + "?gid=152468513&single=true&output=csv"

CACHE_TTL_SECONDS = 300
MAX_PARALLEL_WORKERS = 8


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


def read_sheet(url, sheet, timeout=40):
    response = requests.get(url, timeout=timeout)
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
    Máquinas sem tarefa NÃO aparecem.
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
    Preserva TODAS as máquinas, inclusive as que nunca tiveram tarefa.
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

    ident = machines["Código Interno"].where(machines["Código Interno"].ne(""), "")
    ident = ident.where(ident.ne(""), machines["Equipamento"])
    ident = ident.where(ident.ne(""), machines["Máquina"])
    machines["Identificação"] = ident

    dup = machines["Identificação"].duplicated(keep=False) & machines["Identificação"].ne("")
    machines.loc[dup, "Identificação"] = (
        machines.loc[dup, "Identificação"]
        + " ("
        + machines.loc[dup, "Máquina"]
        + ")"
    )

    return machines.reset_index(drop=True)


# ---------- Configuração de clientes ----------

def _get_secret(key, default=None):
    try:
        sheets = st.secrets.get("sheets", {})
        return sheets.get(key, default)
    except (FileNotFoundError, KeyError, AttributeError):
        return default


def read_consolidation():
    """
    Lê o CSV de consolidação de clientes, quando configurado em
    .streamlit/secrets.toml:

        [sheets]
        consolidation_url = "https://.../consolidacao.csv"

    Colunas esperadas (aliases tolerados):
        cliente, url_master, url_dados
        estado, cidade, região, bairro, estabelecimento (opcionais)
    """
    url = _get_secret("consolidation_url")
    if not url:
        return None

    try:
        response = requests.get(url, timeout=40)
        response.raise_for_status()
        text = response.content.decode("utf-8-sig")
    except Exception:
        return None

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return None

    header = [norm(v) for v in rows[0]]

    def col(*aliases):
        for alias in aliases:
            key = norm(alias)
            if key in header:
                return header.index(key)
        return None

    idx = {
        "cliente": col("cliente", "cliente_nome", "nome_cliente"),
        "estado": col("estado", "uf"),
        "cidade": col("cidade", "municipio", "município"),
        "região": col("regiao", "região"),
        "bairro": col("bairro"),
        "estabelecimento": col("estabelecimento", "unidade", "local"),
        "url_master": col("url_master", "link_master", "master"),
        "url_dados": col("url_dados", "link_dados", "dados"),
    }

    if idx["url_master"] is None or idx["url_dados"] is None:
        return None

    def pick(row, key):
        i = idx[key]
        return clean(row[i]) if i is not None and i < len(row) else ""

    configs = []
    for row in rows[1:]:
        master = pick(row, "url_master")
        dados = pick(row, "url_dados")
        if not master or not dados:
            continue
        configs.append({
            "cliente": pick(row, "cliente"),
            "estado": pick(row, "estado"),
            "cidade": pick(row, "cidade"),
            "região": pick(row, "região"),
            "bairro": pick(row, "bairro"),
            "estabelecimento": pick(row, "estabelecimento"),
            "url_master": master,
            "url_dados": dados,
        })

    return configs or None


def _client_configs():
    """
    Lista de clientes a carregar.
    Com consolidação configurada: lê do CSV.
    Sem consolidação: cai na planilha única atual (retrocompatível).
    """
    consolidated = read_consolidation()
    if consolidated:
        return consolidated
    return [{
        "cliente": "",
        "estado": "",
        "cidade": "",
        "região": "",
        "bairro": "",
        "estabelecimento": "",
        "url_master": URL_ABA_MASTER,
        "url_dados": URL_ABA_DADOS,
    }]


def _enrich_with_location(tasks, registry, config):
    """Anexa metadados do cliente (vindos da consolidação) às duas bases."""
    for column, key in [
        ("Cliente", "cliente"),
        ("Estado", "estado"),
        ("Cidade", "cidade"),
        ("Região", "região"),
        ("Bairro", "bairro"),
        ("Estabelecimento", "estabelecimento"),
    ]:
        value = config.get(key, "")
        if not value:
            continue
        tasks[column] = value
        registry[column] = value
    return tasks, registry


def _load_one_client(config):
    """
    Baixa e normaliza 1 cliente.
    Master e Dados são buscados em paralelo (2 threads por cliente).
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_master = ex.submit(read_sheet, config["url_master"], "Master")
        f_dados = ex.submit(read_sheet, config["url_dados"], "Dados")
        master = f_master.result()
        machines = f_dados.result()

    tasks = normalize_tables(master.copy(), machines.copy())
    registry = normalize_registry(machines.copy())
    return _enrich_with_location(tasks, registry, config)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _load_all_cached():
    """
    Retorna (tasks, registry, elapsed_seconds).
    """
    t0 = time.perf_counter()
    configs = _client_configs()

    if not configs:
        return pd.DataFrame(), pd.DataFrame(), 0.0

    if len(configs) == 1:
        tasks, registry = _load_one_client(configs[0])
    else:
        workers = min(MAX_PARALLEL_WORKERS, len(configs))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_load_one_client, c) for c in configs]
            results = [f.result() for f in futures]

        tasks_frames = [r[0] for r in results if r[0] is not None and not r[0].empty]
        registry_frames = [r[1] for r in results if r[1] is not None and not r[1].empty]

        tasks = (
            pd.concat(tasks_frames, ignore_index=True)
            if tasks_frames else pd.DataFrame()
        )
        registry = (
            pd.concat(registry_frames, ignore_index=True)
            if registry_frames else pd.DataFrame()
        )

    elapsed = time.perf_counter() - t0
    return tasks, registry, round(elapsed, 2)


def load_all():
    """Retorna (tasks, registry). Grava tempo da última carga no estado."""
    tasks, registry, elapsed = _load_all_cached()
    if elapsed and elapsed > 0:
        st.session_state["_last_load_seconds"] = elapsed
    return tasks, registry


def load_and_normalize_data():
    """Compatibilidade com as páginas analíticas — retorna só as tarefas."""
    tasks, _ = load_all()
    return tasks
