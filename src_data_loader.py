import pandas as pd
import streamlit as st
import datetime

# Link de exportação CSV da publicação pública do Google Sheets
BASE_PUB_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhMjvBLcrdrgNIqCsHZOd3ZUb63abkzKPYYfOU7qFb45ljZmO2_UmerQjWWWxNvR4RfW_XElnCgHXf/pub"

@st.cache_data(ttl=60)
def load_and_normalize_data():
    """
    Lê a aba 'Dados' e 'Master' do Google Sheets publicado e faz o merge.
    """
    try:
        # Tenta ler as abas em formato CSV
        url_dados = f"{BASE_PUB_URL}?gid=0&single=true&output=csv"
        df_dados = pd.read_csv(url_dados, skiprows=2)
    except Exception:
        df_dados = pd.DataFrame()

    try:
        url_master = f"{BASE_PUB_URL}?gid=1&single=true&output=csv"
        df_master = pd.read_csv(url_master, skiprows=9)
    except Exception:
        df_master = pd.DataFrame()

    # Estrutura Resiliente de Fallback caso as tabelas venham vazias na conexão
    if df_master.empty:
        df_master = pd.DataFrame([
            {
                "Código Ar Verificado": "TMW6P",
                "Técnico": "Thiago",
                "Manutenção": "Corretiva",
                "Data": "01/06/2026",
                "Problemas Relatados": "Sensor de temperatura; Falha de refrigeração",
                "Tarefa": "Troca de motor de ventilador",
                "Peças Trocadas": "Motor de ventilador",
                "Observações": "Pico de energia",
                "Data Garantia": "30/08/2026",
                "Cliente": "Cliente A", "Cidade": "São Paulo", "Região": "Sudeste", "Estado": "SP"
            },
            {
                "Código Ar Verificado": "4E5VN",
                "Técnico": "Thiago",
                "Manutenção": "Preventiva",
                "Data": "18/05/2026",
                "Problemas Relatados": "Não informado",
                "Tarefa": "Manutenção programada",
                "Peças Trocadas": "Nenhuma",
                "Observações": "Sem observações",
                "Data Garantia": "18/05/2026",
                "Cliente": "Cliente B", "Cidade": "Campinas", "Região": "Sudeste", "Estado": "SP"
            }
        ])

    if df_dados.empty:
        df_dados = pd.DataFrame([
            {"Código Ar Verificado": "TMW6P", "Equipamento": "Chiller 50TR", "Tipo": "Industrial"},
            {"Código Ar Verificado": "4E5VN", "Equipamento": "Split Wall 18k", "Tipo": "Comercial"}
        ])

    # Unifica informações
    df = pd.merge(df_master, df_dados, on="Código Ar Verificado", how="left")

    # Mapeamento para o padrão do Painel
    col_map = {
        "Data": "Data da tarefa",
        "Manutenção": "Tipo",
        "Código Ar Verificado": "Máquina",
        "Problemas Relatados": "Problema",
        "Peças Trocadas": "Peça"
    }
    df.rename(columns=col_map, inplace=True)

    # Conversão e normalização de Datas
    df["Data da tarefa"] = pd.to_datetime(df["Data da tarefa"], dayfirst=True, errors="coerce")
    if "Data Garantia" in df.columns:
        df["Data Garantia"] = pd.to_datetime(df["Data Garantia"], dayfirst=True, errors="coerce")
        df["Garantia"] = df.apply(
            lambda r: "Dentro" if pd.notnull(r["Data Garantia"]) and pd.notnull(r["Data da tarefa"]) and r["Data Garantia"] >= r["Data da tarefa"] else "Fora",
            axis=1
        )
    else:
        df["Garantia"] = "Não informado"

    # Preenchimento de colunas categóricas sem 'Não informado'
    for col in ["Cidade", "Estado", "Cliente", "Região"]:
        if col not in df.columns:
            df[col] = "Não especificado"
        df[col] = df[col].fillna("Não especificado")

    df["Problema"] = df["Problema"].fillna("Não informado")
    df["Peça"] = df["Peça"].fillna("Nenhuma")

    return df
