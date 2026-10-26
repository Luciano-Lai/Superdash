import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

from kpis import (
    TEXT_KPIS,
    PERCENT_KPIS,
    KPI_GOOD_WHEN_UP,
    KPI_BAD_WHEN_UP,
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


def _format_delta_html(name, delta):
    """
    HTML inline com a variação colorida. Retorna "" quando não há
    delta (KPI textual, ou sem base). Nunca devolve 'sem base' — no
    PDF isso é ruído; melhor não desenhar nada.
    """
    if name in TEXT_KPIS or delta is None:
        return ""

    arrow = "▲" if delta > 0 else "▼" if delta < 0 else "≡"
    if name in PERCENT_KPIS:
        d_fmt = f"{abs(delta):.1f} p.p.".replace(".", ",")
    else:
        d_fmt = f"{abs(delta):.1f}%".replace(".", ",")

    if delta == 0:
        color = "#64748B"
    elif (delta > 0 and name in KPI_GOOD_WHEN_UP) or (
        delta < 0 and name in KPI_BAD_WHEN_UP
    ):
        color = "#16A34A"
    else:
        color = "#DC2626"

    return f"<font size='9' color='{color}'>{arrow} {d_fmt}</font>"


def _kpi_card_html(name, value, delta_html):
    label = escape(name)
    val = escape(str(value))
    body = (
        f"<font size='8' color='#64748B'><b>{label.upper()}</b></font>"
        f"<br/><font size='14'><b>{val}</b></font>"
    )
    if delta_html:
        body += f"<br/>{delta_html}"
    return body


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
    styles = getSampleStyleSheet()
    story = []

    if selected_kpis:
        cards = []
        for name in selected_kpis:
            delta_html = _format_delta_html(name, deltas.get(name))
            cards.append(
                Paragraph(
                    _kpi_card_html(name, kpi_dict.get(name, "—"), delta_html),
                    styles["Normal"],
                )
            )
        for start in range(0, len(cards), 4):
            row = cards[start:start + 4]
            row += [""] * (4 - len(row))
            table = Table([row], colWidths=[width / 4] * 4)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1),
                 colors.HexColor("#F0F4F8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), .5,
                 colors.HexColor("#DCE4EC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]))
            story.extend([table, Spacer(1, 12)])
        if chart_figs:
            story.append(PageBreak())

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
                Paragraph(escape(name), styles["Normal"]),
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
