import pandas as pd
import streamlit as st

# Link de exportação CSV direto retornado pela publicação do Google Sheets
CSV_PUB_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?output=csv"

@st.cache_data(ttl=60)
def load_and_normalize_data():
    """
    Lê o CSV publicado diretamente do Google Sheets e normaliza a estrutura.
    """
    try:
        # Lê o CSV público
        df = pd.read_csv(CSV_PUB_URL)
        
        # Se a primeira linha contiver texto descritivo antes do cabeçalho, 
        # localiza a linha que contém as colunas reais
        if "Código Ar Verificado" not in df.columns and "Técnico" not in df.columns:
            # Tenta encontrar a linha do cabeçalho dinamicamente
            df_raw = pd.read_csv(CSV_PUB_URL, header=None)
            header_row_idx = None
            for idx, row in df_raw.iterrows():
                row_str = row.astype(str).values
                if any("Código Ar Verificado" in cell or "Técnico" in cell for cell in row_str):
                    header_row_idx = idx
                    break
            
            if header_row_idx is not None:
                df = pd.read_csv(CSV_PUB_URL, skiprows=header_row_idx)

    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

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

    # Conversão de Datas
    if "Data da tarefa" in df.columns:
        df["Data da tarefa"] = pd.to_datetime(df["Data da tarefa"], dayfirst=True, errors="coerce")
    
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
