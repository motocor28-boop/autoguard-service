from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .config import APP_NAME, APP_VERSION, AUTHOR, REPORT_DIR
from .dtc_database import DTCDatabase
from .obd import DTCResult, VehicleScan
from .solution_engine import DiagnosticGuide, OfflineSolutionDatabase


NAVY = colors.HexColor("#071019")
PANEL = colors.HexColor("#101922")
BLUE = colors.HexColor("#168DFF")
GOLD = colors.HexColor("#E2A72E")
GREEN = colors.HexColor("#20B66A")
ORANGE = colors.HexColor("#F39C12")
RED = colors.HexColor("#E64545")
MUTED = colors.HexColor("#6F7F8F")
BORDER = colors.HexColor("#CBD5DF")
LIGHT = colors.HexColor("#F4F7FA")

SEVERITY_COLORS = {
    "CRÍTICA": RED,
    "ALTA": colors.HexColor("#E55B2D"),
    "MEDIA": ORANGE,
    "BAJA": GREEN,
}


def _safe(value: object) -> str:
    return str(value if value not in (None, "") else "No disponible")


def _shield(canvas: Canvas, x: float, y: float, size: float) -> None:
    canvas.setStrokeColor(GOLD)
    canvas.setFillColor(NAVY)
    canvas.setLineWidth(2)
    path = canvas.beginPath()
    path.moveTo(x, y + size)
    path.lineTo(x + size, y + size * 0.78)
    path.lineTo(x + size * 0.88, y + size * 0.22)
    path.lineTo(x + size * 0.5, y)
    path.lineTo(x + size * 0.12, y + size * 0.22)
    path.close()
    canvas.drawPath(path, fill=1, stroke=1)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", size * 0.32)
    canvas.drawCentredString(x + size * 0.5, y + size * 0.42, "AG")


def _header_footer(canvas: Canvas, doc: BaseDocTemplate) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 22 * mm, width, 22 * mm, fill=1, stroke=0)
    _shield(canvas, 13 * mm, height - 19 * mm, 13 * mm)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(30 * mm, height - 12 * mm, "AUTOGUARD")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawRightString(width - 14 * mm, height - 11 * mm, "SUPERSCAN 2.0 PROFESIONAL")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#BFC9D2"))
    canvas.drawRightString(width - 14 * mm, height - 16 * mm, "DIAGNÓSTICO AUTOMOTRIZ MULTIMARCA · GRÁFICOS HD")

    canvas.setStrokeColor(BORDER)
    canvas.line(14 * mm, 12 * mm, width - 14 * mm, 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(14 * mm, 7.5 * mm, f"Generado por {APP_NAME} · Autor: {AUTHOR}")
    canvas.drawRightString(width - 14 * mm, 7.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=22, textColor=NAVY, spaceAfter=3 * mm))
    styles.add(ParagraphStyle(name="SectionPro", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=14, textColor=NAVY, spaceBefore=4 * mm, spaceAfter=2 * mm, borderColor=BLUE, borderWidth=0, borderPadding=0))
    styles.add(ParagraphStyle(name="SubSection", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=BLUE, spaceBefore=2 * mm, spaceAfter=1.5 * mm))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.7, leading=10, textColor=colors.HexColor("#24313D")))
    styles.add(ParagraphStyle(name="SmallMuted", parent=styles["BodyText"], fontSize=7, leading=9, textColor=MUTED))
    styles.add(ParagraphStyle(name="Action", parent=styles["BodyText"], fontSize=8.2, leading=11, leftIndent=5 * mm, firstLineIndent=-4 * mm, textColor=colors.HexColor("#17212B"), spaceAfter=1.2 * mm))
    styles.add(ParagraphStyle(name="Warning", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#7A3215"), backColor=colors.HexColor("#FFF3E7"), borderColor=ORANGE, borderWidth=0.6, borderPadding=5, spaceBefore=2 * mm, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="CenterSmall", parent=styles["Small"], alignment=TA_CENTER))
    return styles


def _styled_table(data, widths, header_color=NAVY, font_size=7.5, repeat_rows=1):
    table = Table(data, colWidths=widths, repeatRows=repeat_rows)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _severity_distribution(dtcs: Sequence[DTCResult], db: DTCDatabase, solutions: OfflineSolutionDatabase) -> dict[str, int]:
    values = {"CRÍTICA": 0, "ALTA": 0, "MEDIA": 0, "BAJA": 0}
    for item in dtcs:
        record = db.lookup(item.code)
        guide = solutions.lookup(item.code, record.description, record.system)
        values[guide.severity] = values.get(guide.severity, 0) + 1
    return values


def _donut_image(distribution: Mapping[str, int]) -> BytesIO:
    labels = [name for name, value in distribution.items() if value]
    values = [value for value in distribution.values() if value]
    if not values:
        labels, values = ["Sin DTC"], [1]
        palette = ["#20B66A"]
    else:
        palette = [str(SEVERITY_COLORS[name]) for name in labels]
    fig = Figure(figsize=(3.2, 2.2), dpi=160, facecolor="white")
    ax = fig.add_subplot(111)
    ax.pie(values, labels=labels, colors=palette, startangle=90, wedgeprops={"width": 0.38, "edgecolor": "white"}, textprops={"fontsize": 7})
    ax.text(0, 0, str(sum(values) if labels != ["Sin DTC"] else 0), ha="center", va="center", fontsize=18, fontweight="bold")
    ax.set_title("Distribución de severidad", fontsize=9, fontweight="bold")
    fig.tight_layout()
    buffer = BytesIO()
    FigureCanvasAgg(fig).print_png(buffer)
    buffer.seek(0)
    return buffer


def _history_chart(history: Mapping[str, Sequence[tuple[float, float]]], names: Sequence[str]) -> BytesIO | None:
    selected = [(name, list(history.get(name, []))) for name in names]
    selected = [(name, points) for name, points in selected if points]
    if not selected:
        return None
    fig = Figure(figsize=(7.3, max(3.0, 1.25 * len(selected))), dpi=160, facecolor="white")
    axes = fig.subplots(len(selected), 1, squeeze=False)
    palette = ["#168DFF", "#20B66A", "#F39C12", "#8E5BE8", "#E64545", "#2BA7A0"]
    for index, (name, points) in enumerate(selected):
        ax = axes[index][0]
        xs, ys = zip(*points)
        ax.plot(xs, ys, linewidth=1.6, color=palette[index % len(palette)])
        ax.fill_between(xs, ys, alpha=0.08, color=palette[index % len(palette)])
        ax.set_ylabel(name, fontsize=7)
        ax.grid(True, alpha=0.22)
        ax.tick_params(labelsize=6)
    axes[-1][0].set_xlabel("Tiempo de sesión (s)", fontsize=7)
    fig.suptitle("GRÁFICOS HD · DATOS EN VIVO", fontsize=10, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    buffer = BytesIO()
    FigureCanvasAgg(fig).print_png(buffer)
    buffer.seek(0)
    return buffer


def _priority(dtcs: Sequence[DTCResult], db: DTCDatabase, solutions: OfflineSolutionDatabase) -> str:
    order = {"BAJA": 0, "MEDIA": 1, "ALTA": 2, "CRÍTICA": 3}
    highest = "BAJA"
    for item in dtcs:
        record = db.lookup(item.code)
        severity = solutions.lookup(item.code, record.description, record.system).severity
        if order[severity] > order[highest]:
            highest = severity
    return highest if dtcs else "SIN FALLAS"


def generate_professional_report(
    scan: VehicleScan | None,
    dtcs: Iterable[DTCResult],
    live_data: Mapping[str, tuple[float | None, str]],
    history: Mapping[str, Sequence[tuple[float, float]]],
    db: DTCDatabase,
    solutions: OfflineSolutionDatabase,
    metadata: Mapping[str, str] | None = None,
    output_path: Path | None = None,
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = REPORT_DIR / f"Informe_Profesional_SuperScan_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    styles = _styles()
    metadata = dict(metadata or {})
    scan = scan or VehicleScan()
    dtc_list = list(dtcs)
    priority = _priority(dtc_list, db, solutions)
    distribution = _severity_distribution(dtc_list, db, solutions)

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=27 * mm,
        bottomMargin=16 * mm,
        title=f"Informe profesional {APP_NAME}",
        author=AUTHOR,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="professional", frames=[frame], onPage=_header_footer)])

    story = [
        Paragraph("INFORME DE DIAGNÓSTICO VEHICULAR", styles["ReportTitle"]),
        Paragraph(f"Versión {APP_VERSION} · Fecha y hora: {datetime.now():%d-%m-%Y %H:%M:%S}", styles["SmallMuted"]),
        Spacer(1, 3 * mm),
    ]

    vehicle_rows = [
        ["Técnico", metadata.get("tecnico", AUTHOR), "Cliente", metadata.get("cliente", "No informado")],
        ["Vehículo", metadata.get("vehiculo", "No informado"), "Patente", metadata.get("patente", "No informada")],
        ["VIN", _safe(scan.vin), "Kilometraje", metadata.get("kilometraje", "No informado")],
        ["Adaptador", _safe(scan.adapter), "Protocolo", _safe(scan.protocol_name)],
        ["PIDs soportados", str(len(scan.supported_pids)), "Base offline", f"{solutions.count():,} soluciones".replace(",", ".")],
    ]
    story.append(_styled_table(vehicle_rows, [27 * mm, 58 * mm, 27 * mm, 61 * mm], header_color=BLUE, repeat_rows=0))

    story.append(Paragraph("RESUMEN EJECUTIVO", styles["SectionPro"]))
    summary_text = "Sin códigos de falla registrados." if not dtc_list else f"Se detectaron {len(dtc_list)} códigos. La prioridad global estimada es {priority}."
    summary_table = Table([
        [Paragraph(f"<b>Estado general:</b><br/>{summary_text}<br/><br/><b>Resultado:</b> {'Con fallas detectadas' if dtc_list else 'Sin fallas DTC registradas'}", styles["Small"]), Image(_donut_image(distribution), width=67 * mm, height=46 * mm)],
    ], colWidths=[105 * mm, 68 * mm])
    summary_table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (0, 0), LIGHT), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7)]))
    story.append(summary_table)

    story.append(Paragraph("CÓDIGOS ENCONTRADOS", styles["SectionPro"]))
    dtc_rows = [["Código", "Estado", "Sistema", "Severidad", "Descripción"]]
    if not dtc_list:
        dtc_rows.append(["—", "Sin códigos", "—", "BAJA", "No se registraron códigos DTC en la sesión."])
    else:
        for item in dtc_list:
            record = db.lookup(item.code)
            guide = solutions.lookup(item.code, record.description, record.system)
            dtc_rows.append([item.code, item.status, record.system, guide.severity, Paragraph(record.description, styles["Small"])])
    dtc_table = _styled_table(dtc_rows, [18 * mm, 35 * mm, 28 * mm, 21 * mm, 71 * mm], font_size=6.8)
    for row_index, row in enumerate(dtc_rows[1:], start=1):
        severity = row[3]
        dtc_table.setStyle(TableStyle([("TEXTCOLOR", (3, row_index), (3, row_index), SEVERITY_COLORS.get(severity, NAVY)), ("FONTNAME", (3, row_index), (3, row_index), "Helvetica-Bold")]))
    story.append(dtc_table)

    story.append(PageBreak())
    story.append(Paragraph("DATOS EN VIVO DESTACADOS", styles["ReportTitle"]))
    live_rows = [["Parámetro", "Valor", "Unidad", "Mínimo", "Máximo"]]
    if not live_data:
        live_rows.append(["—", "Sin datos", "—", "—", "—"])
    else:
        for name, (value, unit) in live_data.items():
            points = list(history.get(name, []))
            values = [point[1] for point in points]
            formatted = "No disponible" if value is None else f"{value:.2f}"
            live_rows.append([name, formatted, unit, f"{min(values):.2f}" if values else "—", f"{max(values):.2f}" if values else "—"])
    story.append(_styled_table(live_rows, [75 * mm, 27 * mm, 22 * mm, 24 * mm, 24 * mm], header_color=BLUE, font_size=7.2))

    chart = _history_chart(history, ["RPM motor", "Temperatura refrigerante", "Ajuste combustible corto B1", "Ajuste combustible largo B1", "Caudal de combustible", "Nivel de combustible"])
    if chart:
        story.append(Spacer(1, 4 * mm))
        story.append(Image(chart, width=178 * mm, height=106 * mm))
    else:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("No se registró una serie temporal suficiente para incorporar gráficos. Inicie Datos en vivo antes de generar el informe.", styles["Warning"]))

    story.append(Paragraph("PLAN DE ACCIÓN GENERAL", styles["SectionPro"]))
    general_steps = [
        "Conservar los DTC y Freeze Frame originales antes de borrar.",
        "Atender primero códigos críticos, alimentación, comunicación y fallas que puedan generar códigos secundarios.",
        "Realizar inspección visual y mediciones antes de reemplazar componentes.",
        "Seguir especificaciones y diagramas del fabricante para el vehículo exacto.",
        "Validar la reparación mediante datos en vivo, prueba funcional, ciclo de conducción y reescaneo.",
    ]
    for index, step in enumerate(general_steps, start=1):
        story.append(Paragraph(f"<b>{index}.</b> {step}", styles["Action"]))

    story.append(PageBreak())
    story.append(Paragraph("SOLUCIÓN GUIADA POR CÓDIGO", styles["ReportTitle"]))
    if not dtc_list:
        story.append(Paragraph("No existen códigos para desarrollar un plan específico.", styles["Small"]))
    else:
        for dtc_index, item in enumerate(dtc_list):
            record = db.lookup(item.code)
            guide: DiagnosticGuide = solutions.lookup(item.code, record.description, record.system)
            severity_color = SEVERITY_COLORS.get(guide.severity, NAVY)
            heading = Table([[Paragraph(f"<b>{item.code}</b> · {record.description}", styles["Small"]), guide.severity]], colWidths=[145 * mm, 28 * mm])
            heading.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.8, severity_color), ("TEXTCOLOR", (1, 0), (1, 0), severity_color), ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"), ("ALIGN", (1, 0), (1, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            block = [heading, Spacer(1, 2 * mm), Paragraph(guide.summary, styles["Small"])]
            block.append(Paragraph("Síntomas probables", styles["SubSection"]))
            block.extend(Paragraph(f"• {text}", styles["Action"]) for text in guide.symptoms)
            block.append(Paragraph("Causas probables", styles["SubSection"]))
            block.extend(Paragraph(f"• {text}", styles["Action"]) for text in guide.causes)
            block.append(Paragraph("Proceso paso a paso", styles["SubSection"]))
            block.extend(Paragraph(f"<b>{number}.</b> {text}", styles["Action"]) for number, text in enumerate(guide.steps, start=1))
            block.append(Paragraph("Herramientas", styles["SubSection"]))
            block.append(Paragraph(" · ".join(guide.tools), styles["Small"]))
            block.append(Paragraph("Validación final", styles["SubSection"]))
            block.extend(Paragraph(f"☑ {text}", styles["Action"]) for text in guide.validation)
            block.append(Paragraph(f"<b>Seguridad:</b> {guide.safety_notice}", styles["Warning"]))
            story.append(KeepTogether(block))
            if dtc_index < len(dtc_list) - 1:
                story.append(Spacer(1, 4 * mm))

    story.append(PageBreak())
    story.append(Paragraph("CHECKLIST DE CIERRE", styles["ReportTitle"]))
    checklist = [
        "VIN y protocolo registrados",
        "DTC iniciales conservados",
        "Freeze Frame guardado",
        "Inspección visual realizada",
        "Alimentaciones y masas verificadas",
        "Cableado y conectores revisados",
        "Pruebas específicas completadas",
        "Reparación confirmada mediante mediciones",
        "Prueba de ruta realizada cuando corresponde",
        "Reescaneo final sin códigos recurrentes",
    ]
    checklist_rows = [["Estado", "Verificación"]] + [["☐", item] for item in checklist]
    story.append(_styled_table(checklist_rows, [22 * mm, 151 * mm], header_color=GREEN, font_size=8.2))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        "ALCANCE TÉCNICO: La base offline entrega procedimientos orientativos OBD-II y planes de diagnóstico propios. Los pares de apriete, valores eléctricos exactos, diagramas, campañas, programación y procedimientos exclusivos deben verificarse en la documentación del fabricante del vehículo.",
        styles["Warning"],
    ))

    doc.build(story)
    return output_path
