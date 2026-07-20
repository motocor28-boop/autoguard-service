from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .config import APP_NAME, APP_VERSION, AUTHOR, REPORT_DIR
from .dtc_database import DTCDatabase
from .obd import DTCResult, VehicleScan
from .solutions import DTCSolution, SolutionDatabase

NAVY = colors.HexColor("#071B2F")
BLUE = colors.HexColor("#0B74D1")
ORANGE = colors.HexColor("#FF7A00")
LIGHT = colors.HexColor("#F3F6F9")
BORDER = colors.HexColor("#D5DEE8")
MUTED = colors.HexColor("#66788A")
GREEN = colors.HexColor("#199E63")
YELLOW = colors.HexColor("#E6A700")
RED = colors.HexColor("#D83A3A")

SEVERITY_ORDER = {"BAJA": 1, "MEDIA": 2, "ALTA": 3, "CRÍTICA": 4}
SEVERITY_COLOR = {"BAJA": GREEN, "MEDIA": YELLOW, "ALTA": ORANGE, "CRÍTICA": RED}


def _safe(value: object) -> str:
    return str(value if value not in (None, "") else "No disponible")


def _p(text: object, style) -> Paragraph:
    return Paragraph(escape(_safe(text)).replace("\n", "<br/>"), style)


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 12 * mm, width, 12 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawString(14 * mm, height - 7.7 * mm, "AUTOGUARD · SUPERSCAN 2.0 · DIAGNÓSTICO PROFESIONAL")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(14 * mm, 8 * mm, f"Informe técnico generado por {APP_NAME} · Autor: {AUTHOR}")
    canvas.drawRightString(width - 14 * mm, 8 * mm, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def _severity_summary(dtcs: Sequence[DTCResult], solutions: SolutionDatabase) -> tuple[str, Counter[str]]:
    counter: Counter[str] = Counter()
    for item in dtcs:
        counter[solutions.lookup(item.code).severity] += 1
    if not counter:
        return "BAJA", counter
    highest = max(counter, key=lambda value: SEVERITY_ORDER.get(value, 0))
    return highest, counter


def _severity_chart(counter: Counter[str], keepalive: list[BytesIO]) -> Image | None:
    if not counter:
        return None
    labels = [key.title() for key in ("CRÍTICA", "ALTA", "MEDIA", "BAJA") if counter.get(key)]
    values = [counter[key.upper()] for key in labels]
    chart_colors = ["#D83A3A", "#FF7A00", "#E6A700", "#199E63"][: len(values)]
    fig, ax = plt.subplots(figsize=(4.2, 2.5), dpi=150)
    ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=90, colors=chart_colors, wedgeprops={"width": 0.42})
    ax.set_title("Distribución por severidad", fontsize=10, fontweight="bold")
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    keepalive.append(buffer)
    return Image(buffer, width=76 * mm, height=45 * mm)


def _history_chart(
    name: str,
    points: Sequence[tuple[float, float]],
    unit: str,
    keepalive: list[BytesIO],
) -> Image | None:
    if len(points) < 2:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    fig, ax = plt.subplots(figsize=(7.2, 2.5), dpi=160)
    ax.plot(xs, ys, linewidth=1.8)
    ax.fill_between(xs, ys, alpha=0.10)
    ax.set_title(name, fontsize=10, fontweight="bold", loc="left")
    ax.set_xlabel("Tiempo de sesión (s)", fontsize=8)
    ax.set_ylabel(unit, fontsize=8)
    ax.grid(True, alpha=0.25)
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    keepalive.append(buffer)
    return Image(buffer, width=176 * mm, height=58 * mm)


def _styled_table(rows, widths, *, header_color=NAVY, font_size=7.5, repeat_rows=1) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=repeat_rows)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_professional_pdf_report(
    scan: VehicleScan | None,
    dtcs: Iterable[DTCResult],
    live_data: Mapping[str, tuple[float | None, str]],
    history: Mapping[str, Sequence[tuple[float, float]]],
    freeze_data: Mapping[str, tuple[float | None, str]],
    db: DTCDatabase,
    solutions: SolutionDatabase,
    vehicle_meta: Mapping[str, str] | None = None,
    output_path: Path | None = None,
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = REPORT_DIR / f"Informe_Profesional_SuperScan_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontSize=11, leading=15, textColor=BLUE, alignment=TA_CENTER, spaceAfter=5 * mm))
    styles.add(ParagraphStyle(name="SectionPro", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=5 * mm, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="SubsectionPro", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=BLUE, spaceBefore=3 * mm, spaceAfter=1.5 * mm))
    styles.add(ParagraphStyle(name="BodyPro", parent=styles["BodyText"], fontSize=8.4, leading=11.2, textColor=colors.HexColor("#17212B")))
    styles.add(ParagraphStyle(name="SmallPro", parent=styles["Normal"], fontSize=7.2, leading=9, textColor=MUTED))
    styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.white, backColor=BLUE, borderPadding=7))
    styles.add(ParagraphStyle(name="Step", parent=styles["BodyText"], fontSize=8.2, leading=11, leftIndent=4 * mm, firstLineIndent=-4 * mm, spaceAfter=1.2 * mm))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=18 * mm,
        bottomMargin=14 * mm,
        title=f"Informe profesional {APP_NAME}",
        author=AUTHOR,
    )

    scan = scan or VehicleScan()
    dtc_list = list(dtcs)
    meta = dict(vehicle_meta or {})
    highest, severity_counts = _severity_summary(dtc_list, solutions)
    keepalive: list[BytesIO] = []
    story: list[object] = []

    story.extend(
        [
            Spacer(1, 8 * mm),
            Paragraph("AUTOGUARD", styles["CoverTitle"]),
            Paragraph("SUPERSCAN 2.0 · INFORME DE DIAGNÓSTICO VEHICULAR", styles["CoverSub"]),
            HRFlowable(width="100%", thickness=2, color=ORANGE, spaceBefore=1 * mm, spaceAfter=6 * mm),
        ]
    )

    identity_rows = [
        [_p("Fecha y hora", styles["BodyPro"]), _p(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), styles["BodyPro"]), _p("Técnico", styles["BodyPro"]), _p(meta.get("technician", AUTHOR), styles["BodyPro"])],
        [_p("Cliente", styles["BodyPro"]), _p(meta.get("client", "No informado"), styles["BodyPro"]), _p("Patente", styles["BodyPro"]), _p(meta.get("plate", "No informada"), styles["BodyPro"])],
        [_p("VIN", styles["BodyPro"]), _p(scan.vin, styles["BodyPro"]), _p("Kilometraje", styles["BodyPro"]), _p(meta.get("mileage", "No informado"), styles["BodyPro"])],
        [_p("Adaptador", styles["BodyPro"]), _p(scan.adapter, styles["BodyPro"]), _p("Protocolo", styles["BodyPro"]), _p(scan.protocol_name, styles["BodyPro"])],
    ]
    identity = Table(identity_rows, colWidths=[29 * mm, 61 * mm, 29 * mm, 61 * mm])
    identity.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), LIGHT), ("BACKGROUND", (2, 0), (2, -1), LIGHT), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.4, BORDER), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(identity)
    story.append(Spacer(1, 5 * mm))

    state_text = "SIN CÓDIGOS DTC" if not dtc_list else "CON FALLAS DETECTADAS"
    summary_rows = [
        [_p("Estado general", styles["BodyPro"]), _p(state_text, styles["BodyPro"])],
        [_p("Prioridad máxima", styles["BodyPro"]), _p(highest, styles["BodyPro"])],
        [_p("Códigos registrados", styles["BodyPro"]), _p(str(len(dtc_list)), styles["BodyPro"])],
        [_p("PIDs disponibles", styles["BodyPro"]), _p(str(len(scan.supported_pids)), styles["BodyPro"])],
        [_p("Base offline", styles["BodyPro"]), _p(f"{solutions.count():,} planes de acción".replace(",", "."), styles["BodyPro"])],
    ]
    summary_table = Table(summary_rows, colWidths=[48 * mm, 55 * mm])
    summary_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), LIGHT), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.4, BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TEXTCOLOR", (1, 1), (1, 1), SEVERITY_COLOR.get(highest, NAVY)), ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold")]))
    severity_image = _severity_chart(severity_counts, keepalive)
    executive = Table([[summary_table, severity_image or _p("No se registraron fallas.", styles["BodyPro"])]], colWidths=[105 * mm, 75 * mm])
    executive.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.extend([Paragraph("Resumen ejecutivo", styles["SectionPro"]), executive])

    story.append(Paragraph("Códigos encontrados", styles["SectionPro"]))
    dtc_rows = [["Código", "Estado", "Sistema", "Severidad", "Descripción"]]
    if not dtc_list:
        dtc_rows.append(["—", "Sin códigos", "—", "BAJA", _p("No se registraron códigos DTC en la sesión.", styles["BodyPro"])])
    else:
        for item in dtc_list:
            record = db.lookup(item.code)
            solution = solutions.lookup(item.code)
            dtc_rows.append([item.code, item.status, record.system, solution.severity, _p(record.description, styles["BodyPro"])])
    dtc_table = _styled_table(dtc_rows, [18 * mm, 34 * mm, 30 * mm, 22 * mm, 76 * mm], font_size=7.2)
    for row_index in range(1, len(dtc_rows)):
        severity = str(dtc_rows[row_index][3])
        dtc_table.setStyle(TableStyle([("TEXTCOLOR", (3, row_index), (3, row_index), SEVERITY_COLOR.get(severity, NAVY)), ("FONTNAME", (3, row_index), (3, row_index), "Helvetica-Bold")]))
    story.append(dtc_table)

    if dtc_list:
        story.append(PageBreak())
        story.append(Paragraph("Diagnóstico y plan de acción por código", styles["SectionPro"]))
        for index, item in enumerate(dtc_list, start=1):
            record = db.lookup(item.code)
            solution: DTCSolution = solutions.lookup(item.code)
            heading = Table(
                [[_p(f"{item.code} · {record.description}", styles["SubsectionPro"]), _p(solution.severity, styles["SubsectionPro"])]],
                colWidths=[150 * mm, 30 * mm],
            )
            heading.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.8, SEVERITY_COLOR.get(solution.severity, BLUE)), ("ALIGN", (1, 0), (1, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7)]))
            story.append(heading)
            story.append(Spacer(1, 2 * mm))
            detail_rows = [
                [_p("Estado", styles["BodyPro"]), _p(item.status, styles["BodyPro"]), _p("Sistema", styles["BodyPro"]), _p(record.system, styles["BodyPro"])],
                [_p("Alcance", styles["BodyPro"]), _p(record.scope, styles["BodyPro"]), _p("Tipo de guía", styles["BodyPro"]), _p(solution.source_type, styles["BodyPro"])],
            ]
            detail = Table(detail_rows, colWidths=[25 * mm, 65 * mm, 25 * mm, 65 * mm])
            detail.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), LIGHT), ("BACKGROUND", (2, 0), (2, -1), LIGHT), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.35, BORDER), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story.append(detail)
            story.append(Paragraph("Síntomas probables", styles["SubsectionPro"]))
            story.append(_p(" · ".join(solution.symptoms), styles["BodyPro"]))
            story.append(Paragraph("Causas probables", styles["SubsectionPro"]))
            story.append(_p(" · ".join(solution.causes), styles["BodyPro"]))
            story.append(Paragraph("Herramientas recomendadas", styles["SubsectionPro"]))
            story.append(_p(" · ".join(solution.tools), styles["BodyPro"]))
            story.append(Paragraph("Proceso paso a paso", styles["SubsectionPro"]))
            for step_number, step in enumerate(solution.steps, start=1):
                story.append(Paragraph(f"<b>{step_number}.</b> {escape(step)}", styles["Step"]))
            story.append(Paragraph("Validación posterior", styles["SubsectionPro"]))
            for check in solution.validation:
                story.append(Paragraph(f"☐ {escape(check)}", styles["Step"]))
            story.append(_p(solution.notes, styles["SmallPro"]))
            if index < len(dtc_list):
                story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceBefore=4 * mm, spaceAfter=3 * mm))

    story.append(PageBreak())
    story.append(Paragraph("Datos en vivo y gráficos técnicos", styles["SectionPro"]))
    live_rows = [["Parámetro", "Actual", "Unidad", "Mínimo", "Máximo", "Muestras"]]
    if not live_data:
        live_rows.append(["—", "Sin datos", "—", "—", "—", "0"])
    else:
        for name, (value, unit) in live_data.items():
            points = list(history.get(name, []))
            values = [point[1] for point in points]
            actual = "—" if value is None else f"{value:.2f}"
            minimum = "—" if not values else f"{min(values):.2f}"
            maximum = "—" if not values else f"{max(values):.2f}"
            live_rows.append([name, actual, unit, minimum, maximum, str(len(values))])
    story.append(_styled_table(live_rows, [63 * mm, 23 * mm, 19 * mm, 25 * mm, 25 * mm, 25 * mm], header_color=BLUE, font_size=7.2))

    preferred = ["RPM motor", "Temperatura refrigerante", "Ajuste combustible corto B1", "Ajuste combustible largo B1", "Caudal de combustible", "Nivel de combustible", "Voltaje adaptador", "Flujo de aire MAF"]
    graph_count = 0
    for name in preferred:
        points = list(history.get(name, []))
        if len(points) < 2:
            continue
        unit = live_data.get(name, (None, ""))[1]
        image = _history_chart(name, points, unit, keepalive)
        if image:
            story.extend([Spacer(1, 3 * mm), image])
            graph_count += 1
        if graph_count >= 6:
            break
    if graph_count == 0:
        story.append(Spacer(1, 4 * mm))
        story.append(_p("No hubo historial suficiente para generar curvas. Mantenga Datos en vivo activo durante la prueba.", styles["SmallPro"]))

    story.append(Paragraph("Freeze Frame", styles["SectionPro"]))
    freeze_rows = [["Parámetro", "Valor", "Unidad"]]
    if freeze_data:
        for name, (value, unit) in freeze_data.items():
            formatted = "—" if value is None else f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
            freeze_rows.append([name, formatted, unit])
    else:
        freeze_rows.append(["—", "No registrado", "—"])
    story.append(_styled_table(freeze_rows, [100 * mm, 45 * mm, 35 * mm], header_color=ORANGE, font_size=7.5))

    story.append(Paragraph("Checklist de cierre", styles["SectionPro"]))
    checklist = [
        "VIN y datos del vehículo registrados",
        "DTC y Freeze Frame guardados antes de borrar",
        "Inspección visual realizada",
        "Alimentaciones, masas y cableado verificados",
        "Causa raíz identificada con mediciones",
        "Reparación documentada",
        "Prueba funcional o de ruta realizada",
        "Reescaneo final sin códigos pendientes",
        "Monitores OBD-II revisados",
    ]
    checklist_rows = [["Estado", "Verificación"]] + [["☐", _p(item, styles["BodyPro"])] for item in checklist]
    story.append(_styled_table(checklist_rows, [18 * mm, 162 * mm], header_color=NAVY, font_size=7.7))
    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph(
                "El código DTC identifica un sistema o condición, pero no confirma por sí solo la pieza defectuosa. Las decisiones de reparación deben basarse en mediciones, diagramas, procedimientos OEM y condiciones seguras de trabajo.",
                styles["Callout"],
            ),
            Spacer(1, 2 * mm),
            Paragraph(f"Generado con {APP_NAME} versión {APP_VERSION} · Base de soluciones offline: {solutions.count():,} registros".replace(",", "."), styles["SmallPro"]),
        ]
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output_path
