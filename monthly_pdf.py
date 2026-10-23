import io
from datetime import date
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

COR_HEADER = colors.HexColor("#F0F4F8")
COR_GRID = colors.HexColor("#DCE4EC")


def _para(value, style):
    text = (
        "" if value is None or (isinstance(value, float) and pd.isna(value))
        else str(value)
    )
    return Paragraph(escape(text) if text else "—", style)


def _table(rows, col_widths):
    table = Table(rows, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COR_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.5, COR_GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def generate_monthly_pdf(report):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    story = []

    mes_nome = MESES[report["month"] - 1]
    start, end = report["periodo"]

    titulo = "Resumo mensal"
    if report.get("client"):
        titulo += f" — {report['client']}"
    if report.get("ambiente"):
        titulo += f" — {report['ambiente']}"
    story.append(Paragraph(escape(titulo), styles["Title"]))

    story.append(Paragraph(
        f"Competência: {mes_nome}/{report['year']} • "
        f"Período: {start:%d/%m/%Y} a {end:%d/%m/%Y} • "
        f"Situação: "
        f"{'Parcial — mês em andamento' if report['parcial'] else 'Mês completo'}"
        f" • Data de emissão: {date.today():%d/%m/%Y}",
        styles["Normal"],
    ))
    story.append(Paragraph(
        "Relação de máquinas conforme o cadastro atual. "
        "Manutenções referentes à competência selecionada.",
        styles["Italic"],
    ))
    story.append(Spacer(1, 8))

    # ----- Preventivas -----
    story.append(Paragraph("Preventivas no mês", styles["Heading2"]))

    prev = report["preventivas"]
    if prev.empty:
        story.append(Paragraph("Nenhuma máquina no cadastro.", styles["Normal"]))
    else:
        header = [
            "Código interno", "Ambiente PMOC",
            "Última preventiva", "Técnico(s)", "Situação",
        ]
        rows = [[Paragraph(h, styles["Normal"]) for h in header]]
        for _, row in prev.iterrows():
            ult = row.get("Última preventiva")
            ult_str = f"{ult:%d/%m/%Y}" if pd.notna(ult) else "—"
            situacao = (
                "Sem registro de manutenção preventiva neste mês."
                if ult_str == "—" else ""
            )
            rows.append([
                _para(row.get("Identificação"), styles["Normal"]),
                _para(row.get("Ambiente PMOC"), styles["Normal"]),
                _para(ult_str, styles["Normal"]),
                _para(row.get("Técnicos"), styles["Normal"]),
                _para(situacao, styles["Normal"]),
            ])
        story.append(_table(rows, [45 * mm, 35 * mm, 30 * mm, 40 * mm, 30 * mm]))

    # ----- Corretivas -----
    story.append(PageBreak())
    story.append(Paragraph("Corretivas no mês", styles["Heading2"]))

    corr = report["corretivas"]
    if corr.empty:
        story.append(Paragraph(
            "Nenhum atendimento corretivo registrado no mês até a "
            "data de referência.",
            styles["Normal"],
        ))
    else:
        recent = (
            corr.groupby("Identificação")["Data da tarefa"].max()
            .sort_values(ascending=False)
        )
        for ident in recent.index:
            group = corr[corr["Identificação"].eq(ident)].copy()
            group = group.sort_values("Data da tarefa", ascending=False)
            row0 = group.iloc[0]

            story.append(Paragraph(escape(str(ident)), styles["Heading3"]))
            env = escape(str(row0.get("Ambiente PMOC") or "—"))
            story.append(Paragraph(
                f"Ambiente PMOC: {env} • "
                f"Código do sistema: {escape(str(row0['Máquina']))} • "
                f"Atendimentos: {len(group)}",
                styles["Normal"],
            ))

            header = [
                "Data", "Problema relatado",
                "Tarefa executada", "Peça trocada", "Técnico",
            ]
            rows = [[Paragraph(h, styles["Normal"]) for h in header]]
            for _, r in group.iterrows():
                d = r.get("Data da tarefa")
                rows.append([
                    _para(
                        f"{d:%d/%m/%Y}" if pd.notna(d) else "—",
                        styles["Normal"],
                    ),
                    _para(r.get("Problema"), styles["Normal"]),
                    _para(r.get("Tarefa"), styles["Normal"]),
                    _para(r.get("Peça"), styles["Normal"]),
                    _para(r.get("Técnico"), styles["Normal"]),
                ])
            story.append(_table(
                rows, [20 * mm, 55 * mm, 45 * mm, 35 * mm, 25 * mm],
            ))
            story.append(Spacer(1, 8))

    doc.build(story)
    return buffer.getvalue()
