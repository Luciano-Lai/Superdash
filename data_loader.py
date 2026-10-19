import pandas as pd
import streamlit as st

# Link de exportação CSV da publicação pública do Google Sheets
CSV_PUB_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?output=csv"

@st.cache_data(ttl=60)
def load_and_normalize_data():
    """
    Lê o CSV publicado diretamente do Google Sheets e normaliza a estrutura.
    """
    try:
        # Lê o CSV público em formato bruto
        df_raw = pd.read_csv(CSV_PUB_URL, header=None)
        
        if df_raw.empty:
            return pd.DataFrame()

        # Localiza dinamicamente a linha que contém o cabeçalho real
        header_row_idx = None
        for idx, row in df_raw.iterrows():
            # Converte todas as células da linha para string para evitar erro com float/NaN
            row_str_list = [str(cell) for cell in row.values if pd.notnull(cell)]
            if any("Código Ar Verificado" in cell or "Técnico" in cell or "Manutenção" in cell for cell in row_str_list):
                header_row_idx = idx
                break

        if header_row_idx is not None:
            df = pd.read_csv(CSV_PUB_URL, skiprows=header_row_idx)
        else:
            # Caso não encontre a palavra-chave, lê o CSV normalmente
            df = pd.read_csv(CSV_PUB_URL)

    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    # Limpa linhas totalmente vazias e ajusta os nomes das colunas
    df.dropna(how="all", inplace=True)

    # Remove colunas duplicadas mantendo apenas a primeira ocorrência
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.reset_index(drop=True, inplace=True)

    # Mapeamento e padronização dos nomes de colunas
    col_map = {
        "Data": "Data da tarefa",
        "Manutenção": "Tipo",
        "Código Ar Verificado": "Máquina",
        "Problemas Relatados": "Problema",
        "Peças Trocadas": "Peça"
    }
    df.rename(columns=col_map, inplace=True)

    # Conversão e normalização de Datas
    if "Data da tarefa" in df.columns:
        df["Data da tarefa"] = pd.to_datetime(df["Data da tarefa"], dayfirst=True, errors="coerce")
    else:
        # Se por algum motivo a coluna não existir, cria a coluna de data para não quebrar os filtros
        df["Data da tarefa"] = pd.NaT

    if "Data Garantia" in df.columns:
        df["Data Garantia"] = pd.to_datetime(df["Data Garantia"], dayfirst=True, errors="coerce")
        df["Garantia"] = df.apply(
            lambda r: "Dentro" if pd.notnull(r["Data Garantia"]) and pd.notnull(r["Data da tarefa"]) and r["Data Garantia"] >= r["Data da tarefa"] else "Fora",
            axis=1
        )
    else:
        df["Garantia"] = "Não informado"

    # Preenchimento de campos vazios/nulos nas colunas categóricas
    for col in ["Cidade", "Estado", "Cliente", "Região", "Técnico", "Máquina", "Tipo"]:
        if col not in df.columns:
            df[col] = "Não especificado"
        df[col] = df[col].fillna("Não especificado")

    if "Problema" in df.columns:
        df["Problema"] = df["Problema"].fillna("Não informado")
    else:
        df["Problema"] = "Não informado"

    if "Peça" in df.columns:
        df["Peça"] = df["Peça"].fillna("Nenhuma")
    else:
        df["Peça"] = "Nenhuma"

    return df
