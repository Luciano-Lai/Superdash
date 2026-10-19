import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_evolution_chart(df, granularity="Diária", chart_type="Barras"):
    """
    Gera o gráfico de evolução temporal no período.
    """
    df_evo = df.copy()
    if granularity == "Semanal":
        df_evo["Período"] = df_evo["Data da tarefa"].dt.to_period("W").dt.start_time
    elif granularity == "Mensal":
        df_evo["Período"] = df_evo["Data da tarefa"].dt.to_period("M").dt.start_time
    else:
        df_evo["Período"] = df_evo["Data da tarefa"].dt.date

    grouped = df_evo.groupby(["Período", "Tipo"]).size().reset_index(name="Quantidade")

    if chart_type == "Linha":
        fig = px.line(grouped, x="Período", y="Quantidade", color="Tipo", title="Evolução Temporal das Tarefas")
    elif chart_type == "Barras + linha acumulada":
        fig = go.Figure()
        tot_per = df_evo.groupby("Período").size().reset_index(name="Total")
        tot_per["Acumulado"] = tot_per["Total"].cumsum()

        fig.add_trace(go.Bar(x=tot_per["Período"], y=tot_per["Total"], name="Total Diário/Período"))
        fig.add_trace(go.Scatter(x=tot_per["Período"], y=tot_per["Acumulado"], name="Acumulado", yaxis="y2"))
        fig.update_layout(
            title="Evolução com Acumulado",
            yaxis=dict(title="Tarefas no Período"),
            yaxis2=dict(title="Acumulado", overlaying="y", side="right")
        )
    else:
        fig = px.bar(grouped, x="Período", y="Quantidade", color="Tipo", barmode="group", title="Evolução de Tarefas")

    return fig

def render_horizontal_ranking(df, column, title, top_n=10):
    """
    Gera gráficos de ranking em barras horizontais ordenados decrescentemente.
    """
    counts = df[column].value_counts().head(top_n).reset_index()
    counts.columns = [column, "Total"]
    fig = px.bar(counts, x="Total", y=column, orientation="h", title=title, text="Total")
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig

def render_donut_chart(df, column, title, top_n=10, show_others=True):
    """
    Gera gráfico de Rosca com valor total no centro e fatia 'Outras'.
    """
    counts = df[column].value_counts()
    if len(counts) > top_n and show_others:
        top = counts.head(top_n)
        others = pd.Series({"Outras": counts.iloc[top_n:].sum()})
        counts = pd.concat([top, others])
    else:
        counts = counts.head(top_n)

    fig = px.pie(names=counts.index, values=counts.values, hole=0.5, title=title)
    fig.add_annotation(text=f"Total<br><b>{counts.sum()}</b>", showarrow=False, font_size=14)
    return fig
