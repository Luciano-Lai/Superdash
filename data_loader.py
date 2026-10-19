import pandas as pd
import streamlit as st

# Links CSV diretos das abas do Google Sheets
URL_ABA_MASTER = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=1187149031&single=true&output=csv"
URL_ABA_DADOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=152468513&single=true&output=csv"

def parse_sheet_with_header(url):
    """
    Lê o CSV tratando encoding incorreto (UTF-8/CÃ³digo) e detectando
    dinamicamente a linha exata do cabeçalho principal.
    """
    try:
        # Lê em modo texto bruto tratando a codificação
        df_raw = pd.read_csv(url, header=None, encoding="utf-8-sig", on_bad_lines="skip")
        if df_raw.empty:
            return pd.DataFrame()

        header_idx = None
        # Procura a linha que contém o código da máquina ou técnico na tabela real
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(cell) for cell in row.values if pd.notnull(cell)])
            # Busca flexível que tolera erro de codificação UTF-8 ('CÃ³digo' ou 'Codigo')
            if ("digo" in row_str or "Codigo" in row_str or "Técnico" in row_str or "Tecnico" in row_str) and "Equipamento" not in row_str:
                header_idx = idx
                break

        if header_idx is not None:
            df = pd.read_csv(url, skiprows=header_idx, encoding="utf-8-sig")
        else:
            df = pd.read_csv(url, encoding="utf-8-sig")

        # Normaliza os nomes das colunas removendo caracteres estranhos de acentuação
        new_cols = []
        for col in df.columns:
            c = str(col).strip()
            if "CÃ³digo" in c or "digo Ar" in c or "Codigo Ar" in c:
                new_cols.append("Código Ar Verificado")
            elif "TÃ©cnico" in c or "Tecnico" in c:
                new_cols.append("Técnico")
            elif "ManutenÃ§Ã£o" in c or "Manutencao" in c:
                new_cols.append("Manutenção")
            elif "Data" in c and "Garantia" not in c:
                new_cols.append("Data")
            else:
                new_cols.append(c)
        df.columns = new_cols
        return df

    except Exception as e:
        st.error(f"Erro ao ler URL {url}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_and_normalize_data():
    df_master = parse_sheet_with_header(URL_ABA_MASTER)
    df_dados = parse_sheet_with_header(URL_ABA_DADOS)

    if df_master.empty:
        st.warning("Não foi possível carregar os dados da aba Master.")
        return pd.DataFrame()

    # Cruza as tabelas se a chave existir
    if not df_dados.empty and "Código Ar Verificado" in df_dados.columns and "Código Ar Verificado" in df_master.columns:
        df = pd.merge(df_master, df_dados, on="Código Ar Verificado", how="left")
    else:
        df = df_master.copy()

    # Remove linhas vazias ou de separadores de data do Google Sheets
    if "Código Ar Verificado" in df.columns:
        df = df[df["Código Ar Verificado"].notnull()]
        df = df[~df["Código Ar Verificado"].astype(str).str.contains(",", na=False)]

    # Elimina colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.reset_index(drop=True, inplace=True)

    # Mapeamento para o padrão oficial do aplicativo
    col_map = {
        "Data": "Data da tarefa",
        "Manutenção": "Tipo",
        "Código Ar Verificado": "Máquina",
        "Problemas Relatados": "Problema",
        "Peças Trocadas": "Peça"
    }
    df.rename(columns=col_map, inplace=True)

    # Normalização de Datas
    if "Data da tarefa" in df.columns:
        df["Data da tarefa"] = pd.to_datetime(df["Data da tarefa"], errors="coerce", dayfirst=True)

    if "Data Garantia" in df.columns:
        df["Data Garantia"] = pd.to_datetime(df["Data Garantia"], errors="coerce", dayfirst=True)
        df["Garantia"] = df.apply(
            lambda r: "Dentro" if pd.notnull(r["Data Garantia"]) and pd.notnull(r["Data da tarefa"]) and r["Data Garantia"] >= r["Data da tarefa"] else "Fora",
            axis=1
        )
    else:
        df["Garantia"] = "Não informado"

    # Preenchimento de nulos para as opções de filtro
    for col in ["Cidade", "Estado", "Cliente", "Região", "Técnico", "Máquina", "Tipo"]:
        if col not in df.columns:
            df[col] = "Não especificado"
        df[col] = df[col].fillna("Não especificado")

    df["Problema"] = df["Problema"].fillna("Não informado") if "Problema" in df.columns else "Não informado"
    df["Peça"] = df["Peça"].fillna("Nenhuma") if "Peça" in df.columns else "Nenhuma"

    return df
