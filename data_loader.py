import pandas as pd
import streamlit as st

URL_ABA_MASTER = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=1187149031&single=true&output=csv"
URL_ABA_DADOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub?gid=152468513&single=true&output=csv"

def read_raw_csv_resilient(url):
    """
    Tenta ler o CSV testando diferentes encodings (utf-8-sig, latin1, cp1252)
    """
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            df = pd.read_csv(url, header=None, encoding=enc, on_bad_lines="skip")
            if not df.empty and df.shape[1] > 1:
                return df
        except Exception:
            continue
    return pd.DataFrame()

def find_header_and_data(df_raw):
    """
    Localiza a linha onde começam os dados reais (código de máquina, técnico, data, etc.)
    """
    if df_raw.empty:
        return pd.DataFrame()

    header_idx = None
    
    # Varre as linhas procurando os nomes dos cabeçalhos ou dados conhecidos
    for idx, row in df_raw.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notnull(v)])
        
        # Verifica se a linha contém indícios de cabeçalho/dados
        if any(term in row_str for term in ["Código Ar", "Codigo", "CÃ³digo", "TMW6P", "4E5VN", "Técnico", "Tecnico", "Manutenção", "Manutencao"]):
            if any(term in row_str for term in ["TMW6P", "4E5VN"]) and idx > 0:
                header_idx = idx - 1
            else:
                header_idx = idx
            break

    if header_idx is not None:
        # Usa a linha encontrada como cabeçalho
        new_header = df_raw.iloc[header_idx].astype(str).str.strip().values
        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = new_header
    else:
        # Se não achou marcador, usa a primeira linha
        new_header = df_raw.iloc[0].astype(str).str.strip().values
        df = df_raw.iloc[1:].copy()
        df.columns = new_header

    return df

@st.cache_data(ttl=60)
def load_and_normalize_data():
    df_raw_master = read_raw_csv_resilient(URL_ABA_MASTER)
    df_raw_dados = read_raw_csv_resilient(URL_ABA_DADOS)

    # EXIBE DIAGNÓSTICO NA TELA DO STREAMLIT SE HOUVER PROBLEMA
    if df_raw_master.empty:
        st.error("⚠️ Não foi possível baixar os dados da URL Master. Verifique se a planilha está publicada na web.")
        return pd.DataFrame()

    with st.expander("🛠️ Diagnóstico do Leitor de CSV (Clique para expandir)"):
        st.write("Linhas brutas da Aba Master (Primeiras 10 linhas):")
        st.dataframe(df_raw_master.head(10))

    df_master = find_header_and_data(df_raw_master)
    df_dados = find_header_and_data(df_raw_dados)

    # Padroniza nomes de colunas
    def clean_column_names(df):
        cols = []
        for c in df.columns:
            col_s = str(c)
            if any(k in col_s for k in ["digo Ar", "Codigo Ar", "CÃ³digo"]):
                cols.append("Código Ar Verificado")
            elif any(k in col_s for k in ["TÃ©cnico", "Tecnico", "Técnico"]):
                cols.append("Técnico")
            elif any(k in col_s for k in ["ManutenÃ§Ã£o", "Manutencao", "Manutenção"]):
                cols.append("Manutenção")
            elif "Data" in col_s and "Garantia" not in col_s:
                cols.append("Data da tarefa")
            elif "Garantia" in col_s:
                cols.append("Data Garantia")
            elif any(k in col_s for k in ["Problema", "Problemas"]):
                cols.append("Problema")
            elif any(k in col_s for k in ["PeÃ§a", "Peca", "Peças"]):
                cols.append("Peça")
            else:
                cols.append(col_s.strip())
        df.columns = cols
        return df

    df_master = clean_column_names(df_master)
    if not df_dados.empty:
        df_dados = clean_column_names(df_dados)

    # Merge das tabelas
    if not df_dados.empty and "Código Ar Verificado" in df_dados.columns and "Código Ar Verificado" in df_master.columns:
        df = pd.merge(df_master, df_dados, on="Código Ar Verificado", how="left")
    else:
        df = df_master.copy()

    # Limpeza de colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.reset_index(drop=True, inplace=True)

    # Garante renomeação e existência de colunas essenciais
    col_map = {
        "Data": "Data da tarefa",
        "Manutenção": "Tipo",
        "Código Ar Verificado": "Máquina"
    }
    df.rename(columns=col_map, inplace=True)

    if "Data da tarefa" not in df.columns:
        df["Data da tarefa"] = pd.NaT
    else:
        df["Data da tarefa"] = pd.to_datetime(df["Data da tarefa"], errors="coerce", dayfirst=True)

    # Limpa linhas inválidas ou completamente vazias
    if "Máquina" in df.columns:
        df = df[df["Máquina"].notnull()]
        df = df[~df["Máquina"].astype(str).str.contains("^,", na=False)]

    for col in ["Cidade", "Estado", "Cliente", "Região", "Técnico", "Máquina", "Tipo"]:
        if col not in df.columns:
            df[col] = "Não especificado"
        df[col] = df[col].fillna("Não especificado")

    df["Problema"] = df["Problema"].fillna("Não informado") if "Problema" in df.columns else "Não informado"
    df["Peça"] = df["Peça"].fillna("Nenhuma") if "Peça" in df.columns else "Nenhuma"

    return df
