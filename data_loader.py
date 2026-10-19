import pandas as pd
import streamlit as st

# Links CSV diretos das abas do Google Sheets
URL_ABA_MASTER = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=1187149031&single=true&output=csv"
URL_ABA_DADOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=152468513&single=true&output=csv"

def parse_sheet_with_header(url):
    """
    Lê o CSV tratando encoding incorreto e detectando dinamicamente
    a linha do cabeçalho principal.
    """
    try:
        df_raw = pd.read_csv(url, header=None, encoding="utf-8-sig", on_bad_lines="skip")
        if df_raw.empty:
            return pd.DataFrame()

        header_idx = None
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(cell) for cell in row.values if pd.notnull(cell)])
            # Procura por palavras-chave na linha real da tabela
            if ("digo" in row_str or "Codigo" in row_str or "Técnico" in row_str or "Tecnico" in row_str or "TMW6P" in row_str or "4E5VN" in row_str):
                # Se for a linha dos dados (ex: TMW6P), o cabeçalho é a linha imediatamente anterior
                if "TMW6P" in row_str or "4E5VN" in row_str:
                    header_idx = max(0, idx - 1)
                else:
                    header_idx = idx
                break

        if header_idx is not None:
            df = pd.read_csv(url, skiprows=header_idx, encoding="utf-8-sig")
        else:
            df = pd.read_csv(url, encoding="utf-8-sig")

        # Mapeamento e normalização robusta das colunas
        new_cols = []
        for col in df.columns:
            c = str(col).strip()
            if any(k in c for k in ["CÃ³digo", "digo Ar", "Codigo Ar"]):
                new_cols.append("Código Ar Verificado")
            elif any(k in c for k in ["TÃ©cnico", "Tecnico"]):
                new_cols.append("Técnico")
            elif any(k in c for k in ["ManutenÃ§Ã£o", "Manutencao"]):
                new_cols.append("Manutenção")
            elif "Data" in c and "Garantia" not in c:
                new_cols.append("Data da tarefa")
            elif "Garantia" in c:
                new_cols.append("Data Garantia")
            elif any(k in c for k in ["Problema", "Problemas"]):
                new_cols.append("Problema")
            elif any(k in c for k in ["PeÃ§a", "Peca", "Peças"]):
                new_cols.append("Peça")
            else:
                new_cols.append(c)
        
        df.columns = new_cols
        return df

    except Exception as e:
        st.error(f"Erro ao ler URL do Google Sheets: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_and_normalize_data():
    df_master = parse_sheet_with_header(URL_ABA_MASTER)
    df_dados = parse_sheet_with_header(URL_ABA_DADOS)

    if df_master.empty:
        # Retorna DataFrame com estrutura mínima para evitar KeyError
        return pd.DataFrame(columns=["Data da tarefa", "Tipo", "Máquina", "Técnico", "Cliente", "Cidade", "Região", "Estado"])

    # Realiza a fusão entre as duas abas se a chave existir
    if not df_dados.empty and "Código Ar Verificado" in df_dados.columns and "Código Ar Verificado" in df_master.columns:
        df = pd.merge(df_master, df_dados, on="Código Ar Verificado", how="left")
    else:
        df = df_master.copy()

    # Remove linhas de lixo ou rodapés
    if "Código Ar Verificado" in df.columns:
        df = df[df["Código Ar Verificado"].notnull()]
        df = df[~df["Código Ar Verificado"].astype(str).str.contains(",", na=False)]

    # Remove colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.reset_index(drop=True, inplace=True)

    # Renomeação final de segurança
    col_map = {
        "Data": "Data da tarefa",
        "Manutenção": "Tipo",
        "Código Ar Verificado": "Máquina"
    }
    df.rename(columns=col_map, inplace=True)

    # GARANTIA DE SEGURANÇA: Se a coluna "Data da tarefa" não existir, cria como NaT
    if "Data da tarefa" not in df.columns:
        df["Data da tarefa"] = pd.NaT
    else:
        df["Data da tarefa"] = pd.to_datetime(df["Data da tarefa"], errors="coerce", dayfirst=True)

    # Garantia de colunas de garantia
    if "Data Garantia" in df.columns:
        df["Data Garantia"] = pd.to_datetime(df["Data Garantia"], errors="coerce", dayfirst=True)
        df["Garantia"] = df.apply(
            lambda r: "Dentro" if pd.notnull(r["Data Garantia"]) and pd.notnull(r["Data da tarefa"]) and r["Data Garantia"] >= r["Data da tarefa"] else "Fora",
            axis=1
        )
    else:
        df["Garantia"] = "Não informado"

    # Preenchimento de campos categóricos para os filtros
    for col in ["Cidade", "Estado", "Cliente", "Região", "Técnico", "Máquina", "Tipo"]:
        if col not in df.columns:
            df[col] = "Não especificado"
        df[col] = df[col].fillna("Não especificado")

    df["Problema"] = df["Problema"].fillna("Não informado") if "Problema" in df.columns else "Não informado"
    df["Peça"] = df["Peça"].fillna("Nenhuma") if "Peça" in df.columns else "Nenhuma"

    return df
