import pandas as pd
import streamlit as st

# Links diretos para cada aba do Google Sheets via CSV
URL_ABA_MASTER = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=1187149031&single=true&output=csv"
URL_ABA_DADOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=152468513&single=true&output=csv"

def parse_sheet_with_header(url):
    """
    Lê o CSV de uma aba do Google Sheets, detectando automaticamente
    a linha onde estão localizados os nomes das colunas.
    """
    try:
        df_raw = pd.read_csv(url, header=None)
        if df_raw.empty:
            return pd.DataFrame()

        header_idx = None
        keywords = ["Código Ar Verificado", "Técnico", "Manutenção", "Equipamento", "Cliente", "Data"]

        for idx, row in df_raw.iterrows():
            row_str = [str(cell) for cell in row.values if pd.notnull(cell)]
            if any(k in cell for cell in row_str for k in keywords):
                header_idx = idx
                break

        if header_idx is not None:
            return pd.read_csv(url, skiprows=header_idx)
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Erro ao carregar a aba do link {url}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_and_normalize_data():
    """
    Carrega as duas abas, cruza os dados e normaliza a estrutura para o painel.
    """
    df_master = parse_sheet_with_header(URL_ABA_MASTER)
    df_dados = parse_sheet_with_header(URL_ABA_DADOS)

    if df_master.empty:
        st.warning("A aba principal (Master) retornou vazia ou inacessível.")
        return pd.DataFrame()

    # Cruza os dados das duas abas se a chave existir em ambas
    if not df_dados.empty and "Código Ar Verificado" in df_dados.columns and "Código Ar Verificado" in df_master.columns:
        df = pd.merge(df_master, df_dados, on="Código Ar Verificado", how="left")
    else:
        df = df_master.copy()

    # Remove colunas duplicadas mantendo a primeira ocorrência
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.reset_index(drop=True, inplace=True)

    # Padronização de nomes de colunas
    col_map = {
        "Data": "Data da tarefa",
        "Manutenção": "Tipo",
        "Código Ar Verificado": "Máquina",
        "Problemas Relatados": "Problema",
        "Peças Trocadas": "Peça"
    }
    df.rename(columns=col_map, inplace=True)

    # Tratamento da coluna de datas
    if "Data da tarefa" in df.columns:
        df["Data da tarefa"] = pd.to_datetime(df["Data da tarefa"], errors="coerce", dayfirst=True)
    else:
        df["Data da tarefa"] = pd.NaT

    if "Data Garantia" in df.columns:
        df["Data Garantia"] = pd.to_datetime(df["Data Garantia"], errors="coerce", dayfirst=True)
        df["Garantia"] = df.apply(
            lambda r: "Dentro" if pd.notnull(r["Data Garantia"]) and pd.notnull(r["Data da tarefa"]) and r["Data Garantia"] >= r["Data da tarefa"] else "Fora",
            axis=1
        )
    else:
        df["Garantia"] = "Não informado"

    # Preenchimento de nulos para categorias do filtro
    for col in ["Cidade", "Estado", "Cliente", "Região", "Técnico", "Máquina", "Tipo"]:
        if col not in df.columns:
            df[col] = "Não especificado"
        df[col] = df[col].fillna("Não especificado")

    df["Problema"] = df["Problema"].fillna("Não informado") if "Problema" in df.columns else "Não informado"
    df["Peça"] = df["Peça"].fillna("Nenhuma") if "Peça" in df.columns else "Nenhuma"

    return df
