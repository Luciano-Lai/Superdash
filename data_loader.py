import pandas as pd
import streamlit as st

URL_ABA_MASTER = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=1187149031&single=true&output=csv"
URL_ABA_DADOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=152468513&single=true&output=csv"

def parse_sheet_by_fixed_header(url):
    """
    Lê o CSV localizando exatamente a linha que contém as colunas
    'Código Ar Verificado' e 'Técnico' (linha 8 no Google Sheets).
    """
    for enc in ["utf-8-sig", "latin1", "cp1252"]:
        try:
            df_raw = pd.read_csv(url, header=None, encoding=enc, on_bad_lines="skip")
            if df_raw.empty:
                continue

            # Localiza a linha exata onde estão os cabeçalhos da tabela principal
            header_idx = None
            for idx, row in df_raw.iterrows():
                row_values = [str(val).strip() for val in row.values if pd.notnull(val)]
                # Procura pela linha que contém 'Código Ar' ou 'Técnico' junto com 'Manutenção'
                if any("Código Ar" in v or "Codigo Ar" in v or "CÃ³digo" in v for v in row_values) and \
                   any("Técnico" in v or "Tecnico" in v or "Manutenção" in v or "Manutencao" in v for v in row_values):
                    header_idx = idx
                    break

            if header_idx is not None:
                # Extrai os nomes das colunas e os dados a partir das linhas seguintes
                cols = df_raw.iloc[header_idx].astype(str).str.strip().values
                df = df_raw.iloc[header_idx + 1:].copy()
                df.columns = cols
                return df
            else:
                # Se não encontrar por palavra-chave, pula as 8 primeiras linhas de cabeçalho superior
                df = pd.read_csv(url, skiprows=8, encoding=enc)
                return df
        except Exception:
            continue

    return pd.DataFrame()

@st.cache_data(ttl=60)
def load_and_normalize_data():
    df_master = parse_sheet_by_fixed_header(URL_ABA_MASTER)
    df_dados = parse_sheet_by_fixed_header(URL_ABA_DADOS)

    if df_master.empty:
        st.error("⚠️ Não foi possível carregar os dados da aba Master.")
        return pd.DataFrame()

    # Limpa colunas sem nome ou vazias
    df_master = df_master.loc[:, ~df_master.columns.str.contains('^Unnamed|^None', na=False)]
    if not df_dados.empty:
        df_dados = df_dados.loc[:, ~df_dados.columns.str.contains('^Unnamed|^None', na=False)]

    # Normalização dos nomes das colunas
    def normalize_cols(df):
        cols = []
        for c in df.columns:
            c_str = str(c).strip()
            if any(k in c_str for k in ["digo Ar", "Codigo Ar", "CÃ³digo"]):
                cols.append("Código Ar Verificado")
            elif any(k in c_str for k in ["TÃ©cnico", "Tecnico", "Técnico"]):
                cols.append("Técnico")
            elif any(k in c_str for k in ["ManutenÃ§Ã£o", "Manutencao", "Manutenção"]):
                cols.append("Manutenção")
            elif "Data" in c_str and "Garantia" not in c_str and "Aquisição" not in c_str:
                cols.append("Data da tarefa")
            elif "Garantia" in c_str:
                cols.append("Data Garantia")
            elif any(k in c_str for k in ["Problema", "Problemas"]):
                cols.append("Problema")
            elif any(k in c_str for k in ["PeÃ§a", "Peca", "Peças"]):
                cols.append("Peça")
            else:
                cols.append(c_str)
        df.columns = cols
        return df

    df_master = normalize_cols(df_master)
    if not df_dados.empty:
        df_dados = normalize_cols(df_dados)

    # Realiza o merge entre a aba Master e a aba Dados pelo Código Ar Verificado
    if not df_dados.empty and "Código Ar Verificado" in df_dados.columns and "Código Ar Verificado" in df_master.columns:
        df = pd.merge(df_master, df_dados, on="Código Ar Verificado", how="left")
    else:
        df = df_master.copy()

    # Remove colunas duplicadas mantendo a primeira ocorrência
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.reset_index(drop=True, inplace=True)

    # Mapeamento final de renomeação
    col_map = {
        "Data": "Data da tarefa",
        "Manutenção": "Tipo",
        "Código Ar Verificado": "Máquina"
    }
    df.rename(columns=col_map, inplace=True)

    # Filtra linhas válidas (ignora linhas sem máquina ou preenchidas com 'None')
    if "Máquina" in df.columns:
        df = df[df["Máquina"].notnull()]
        df = df[~df["Máquina"].astype(str).str.strip().isin(["None", "nan", ""])]

    # Tratamento de Datas
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

    # Preenchimento de campos vazios para os filtros
    for col in ["Cidade", "Estado", "Cliente", "Região", "Técnico", "Máquina", "Tipo"]:
        if col not in df.columns:
            df[col] = "Não especificado"
        df[col] = df[col].fillna("Não especificado")

    df["Problema"] = df["Problema"].fillna("Não informado") if "Problema" in df.columns else "Não informado"
    df["Peça"] = df["Peça"].fillna("Nenhuma") if "Peça" in df.columns else "Nenhuma"

    return df
