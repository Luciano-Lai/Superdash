import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)


TEXT_KPIS = {"Problema mais frequente", "Peça mais trocada"}
PERCENT_KPIS = {"% Preventivas", "% Corretivas"}
KPI_GOOD_WHEN_UP = {"Preventivas", "% Preventivas"}
KPI_BAD_WHEN_UP = {
    "Corretivas", "% Corretivas",
    "Corretivas em garantia", "Corretivas fora da garantia",
}

STYLES = getSampleStyleSheet()

LABEL_STYLE = ParagraphStyle(
    "kpi_label",
    parent=STYLES["Normal"],
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#64748B"),
    fontName="Helvetica-Bold",
)

VALUE_STYLE = ParagraphStyle(
    "kpi_value",
    parent=STYLES["Normal"],
    fontSize=20,
    leading=24,
    textColor=colors.HexColor("#0F172A"),
    fontName="Helvetica-Bold",
)

TEXT_VALUE_STYLE = ParagraphStyle(
    "kpi_value_text",
    parent=STYLES["Normal"],
    fontSize=11,
    leading=14,
    textColor=colors.HexColor("#0F172A"),
    fontName="Helvetica-Bold",
)

BADGE_STYLE_GOOD = ParagraphStyle(
    "badge_good",
    parent=STYLES["Normal"],
    fontSize=9,
    leading=11,
    textColor=colors.HexColor("#15803D"),
    fontName="Helvetica-Bold",
)
BADGE_STYLE_BAD = ParagraphStyle(
    "badge_bad",
    parent=STYLES["Normal"],
    fontSize=9,
    leading=11,
    textColor=colors.HexColor("#B91C1C"),
    fontName="Helvetica-Bold",
)
BADGE_STYLE_FLAT = ParagraphStyle(
    "badge_flat",
    parent=STYLES["Normal"],
    fontSize=9,
    leading=11,
    textColor=colors.HexColor("#64748B"),
    fontName="Helvetica-Bold",
)


def _figure_bytes(fig, target_width=1100):
    height_px = int(fig.layout.height or 650)
    if height_px <= 0:
        height_px = 650
    width_px = target_width
    buf = fig.to_image(
        format="png", width=width_px, height=height_px, scale=1,
    )
    return buf, height_px / width_px


def _fit_image(fig, max_w, max_h):
    max_w = float(max_w)
    max_h = float(max_h)
    if max_w <= 0 or max_h <= 0:
        raise ValueError(
            "Área da imagem inválida para o PDF (célula muito pequena)."
        )
    buf, aspect = _figure_bytes(fig)
    if max_w * aspect <= max_h:
        w = max_w
        h = max_w * aspect
    else:
        h = max_h
        w = max_h / aspect
    return Image(io.BytesIO(buf), width=w, height=h)


def _badge_for(name, delta):
    """Retorna um mini-Table com fundo colorido, imitando o badge da tela."""
    if name in TEXT_KPIS or delta is None:
        return None

    arrow = "▲" if delta > 0 else "▼" if delta < 0 else "≡"
    if name in PERCENT_KPIS:
        d_fmt = f"{abs(delta):.1f} p.p.".replace(".", ",")
    else:
        d_fmt = f"{abs(delta):.1f}%".replace(".", ",")

    if delta == 0:
        style = BADGE_STYLE_FLAT
        bg = "#F1F5F9"
    elif (delta > 0 and name in KPI_GOOD_WHEN_UP) or (
        delta < 0 and name in KPI_BAD_WHEN_UP
    ):
        style = BADGE_STYLE_GOOD
        bg = "#DCFCE7"
    else:
        style = BADGE_STYLE_BAD
        bg = "#FEE2E2"

    badge = Table(
        [[Paragraph(f"{arrow} {d_fmt}", style)]],
        colWidths=[None],
    )
    badge.hAlign = "LEFT"
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return badge


def _card(name, value, delta, inner_w):
    """
    Monta o card como uma Table aninhada de até 3 linhas:
      label (uppercase cinza)
      valor (grande) ou texto (médio)
      badge de delta (se aplicável)
    """
    if name in TEXT_KPIS:
        value_paragraph = Paragraph(escape(str(value)), TEXT_VALUE_STYLE)
    else:
        value_paragraph = Paragraph(escape(str(value)), VALUE_STYLE)

    rows = [
        [Paragraph(escape(name.upper()), LABEL_STYLE)],
        [value_paragraph],
    ]

    badge = _badge_for(name, delta)
    if badge is not None:
        rows.append([badge])

    card = Table(rows, colWidths=[inner_w])
    card.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))
    return card


def generate_pdf_report(
    kpi_dict,
    selected_kpis,
    chart_figs=None,
    charts_per_page=1,
    deltas=None,
):
    if not 1 <= charts_per_page <= 4:
        raise ValueError("Escolha de 1 a 4 gráficos por página.")
    chart_figs = chart_figs or {}
    deltas = deltas or {}
    if not selected_kpis and not chart_figs:
        raise ValueError("Selecione ao menos um indicador ou gráfico.")

    buffer = io.BytesIO()
    page = landscape(A4)
    width, height = page[0] - 60, page[1] - 60
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    story = []

    # ---------- Cartões de KPI ----------
    if selected_kpis:
        cell_w = width / 4
        inner_w = cell_w - 20      # 10pt de padding lateral por célula

        for start in range(0, len(selected_kpis), 4):
            row = []
            for name in selected_kpis[start:start + 4]:
                card = _card(
                    name,
                    kpi_dict.get(name, "—"),
                    deltas.get(name),
                    inner_w,
                )
                row.append(card)
            while len(row) < 4:
                row.append("")

            table = Table([row], colWidths=[cell_w] * 4)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1),
                 colors.HexColor("#F0F4F8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), .5,
                 colors.HexColor("#DCE4EC")),
                ("LINEAFTER", (0, 0), (-2, -1), .5,
                 colors.HexColor("#DCE4EC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]))
            story.extend([table, Spacer(1, 12)])

        if chart_figs:
            story.append(PageBreak())

    # ---------- Gráficos ----------
    entries = list(chart_figs.items())
    columns = 1 if charts_per_page == 1 else 2
    rows = 1 if charts_per_page <= 2 else 2
    cell_w = width / columns
    cell_h = (height - 12) / rows

    for start in range(0, len(entries), charts_per_page):
        chunk = entries[start:start + charts_per_page]
        cells = []
        for name, fig in chunk:
            img = _fit_image(fig, cell_w - 14, cell_h - 32)
            cells.append([
                Paragraph(escape(name), STYLES["Normal"]),
                img,
            ])
        while len(cells) < rows * columns:
            cells.append("")

        grid = [cells[i:i + columns] for i in range(0, len(cells), columns)]
        table = Table(grid, colWidths=[cell_w] * columns)
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(table)
        if start + charts_per_page < len(entries):
            story.append(PageBreak())

    doc.build(story)
    return buffer.getvalue()
