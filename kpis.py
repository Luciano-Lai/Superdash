import pandas as pd

def calculate_executive_kpis(df: pd.DataFrame) -> dict:
    """Calcula os indicadores estratégicos executivos."""
    if df.empty:
        return {
            "total_chamados": 0,
            "preventivas": 0,
            "corretivas": 0,
            "garantia_qtd": 0,
            "pct_garantia": 0.0,
            "pct_preventivas": 0.0
        }

    total = len(df)
    
    # Tipo de Manutenção
    if "Tipo" in df.columns:
        preventivas = len(df[df["Tipo"].astype(str).str.contains("Preventiva", case=False, na=False)])
        corretivas = len(df[df["Tipo"].astype(str).str.contains("Corretiva", case=False, na=False)])
    else:
        preventivas = 0
        corretivas = 0

    # Garantia
    garantia_qtd = len(df[df["Garantia"] == "Dentro"]) if "Garantia" in df.columns else 0

    pct_garantia = (garantia_qtd / total * 100) if total > 0 else 0.0
    pct_preventivas = (preventivas / total * 100) if total > 0 else 0.0

    return {
        "total_chamados": total,
        "preventivas": preventivas,
        "corretivas": corretivas,
        "garantia_qtd": garantia_qtd,
        "pct_garantia": pct_garantia,
        "pct_preventivas": pct_preventivas
    }