from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = colors.HexColor("#FF7A00")
BRAND_DARK = colors.HexColor("#B94E00")
DARK = colors.HexColor("#111820")
MID = colors.HexColor("#394554")
LIGHT = colors.HexColor("#F1F3F6")
GREEN = colors.HexColor("#239B65")
RED = colors.HexColor("#C73E45")
YELLOW = colors.HexColor("#D99B19")


def _safe(value: object) -> str:
    text = str(value or "No informado").strip()
    return text or "No informado"


def _paragraph(text: object, style) -> Paragraph:
    return Paragraph(_safe(text).replace("\n", "<br/>"), style)


def default_report_path() -> Path:
    documents = Path.home() / "Documents" / "AUTOGUARD" / "Informes"
    documents.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return documents / f"Informe_PREMIUM_AUTOGUARD_{stamp}.pdf"


def _severity_color(severity: str):
    value = severity.casefold()
    if "alta" in value or "crítica" in value or "critica" in value:
        return RED
    if "media" in value:
        return YELLOW
    return GREEN


def _chart(title: str, samples: list[tuple[float, float]], width: float = 174 * mm, height: float = 66 * mm) -> Drawing:
    drawing = Drawing(width, height)
    if not samples:
        drawing.add(String(10, height / 2, "Sin muestras", fontName="Helvetica", fontSize=9, fillColor=MID))
        return drawing
    if len(samples) > 180:
        step = max(1, len(samples) // 180)
        samples = samples[::step]
    start = samples[0][0]
    points = [(float(timestamp - start), float(value)) for timestamp, value in samples]
    chart = LinePlot()
    chart.x = 44
    chart.y = 28
    chart.width = width - 62
    chart.height = height - 54
    chart.data = [points]
    chart.joinedLines = 1
    chart.lines[0].strokeColor = BRAND
    chart.lines[0].strokeWidth = 2
    chart.xValueAxis.valueMin = min(point[0] for point in points)
    chart.xValueAxis.valueMax = max(max(point[0] for point in points), chart.xValueAxis.valueMin + 1)
    values = [point[1] for point in points]
    minimum = min(values)
    maximum = max(values)
    margin = max((maximum - minimum) * 0.12, 0.5)
    chart.yValueAxis.valueMin = minimum - margin
    chart.yValueAxis.valueMax = maximum + margin
    chart.xValueAxis.labelTextFormat = "%.0f"
    chart.yValueAxis.labelTextFormat = "%.1f"
    chart.xValueAxis.labels.fontName = "Helvetica"
    chart.yValueAxis.labels.fontName = "Helvetica"
    chart.xValueAxis.labels.fontSize = 7
    chart.yValueAxis.labels.fontSize = 7
    chart.xValueAxis.strokeColor = MID
    chart.yValueAxis.strokeColor = MID
    chart.xValueAxis.gridStrokeColor = colors.HexColor("#D9DEE5")
    chart.yValueAxis.gridStrokeColor = colors.HexColor("#D9DEE5")
    drawing.add(chart)
    drawing.add(String(5, height - 14, title, fontName="Helvetica-Bold", fontSize=10, fillColor=DARK))
    drawing.add(String(width - 80, 5, "Tiempo [s]", fontName="Helvetica", fontSize=7, fillColor=MID))
    drawing.add(String(5, 5, f"mín {minimum:.2f} · máx {maximum:.2f}", fontName="Helvetica", fontSize=7, fillColor=MID))
    return drawing


def generate_pdf_report(
    output: Path,
    vehicle: Mapping[str, object],
    protocol: str,
    dtcs: Iterable[Mapping[str, object]],
    live_values: Mapping[str, object],
    history: Mapping[str, Iterable[tuple[float, float]]] | None = None,
    notes: str = "",
    author: str = "Esteban Cortez Richards",
    version: str = "6.2 PREMIUM",
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AGBrand", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=25, alignment=TA_CENTER, textColor=BRAND, spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AGSubtitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, alignment=TA_CENTER, textColor=DARK, spaceAfter=6 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AGSection", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=BRAND_DARK, spaceBefore=5 * mm, spaceAfter=2.5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AGBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.5, leading=11.5, textColor=DARK, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="AGSmall", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=7.3, leading=9.4, textColor=MID,
    ))
    styles.add(ParagraphStyle(
        name="AGCode", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=14, leading=17, textColor=BRAND,
    ))
    styles.add(ParagraphStyle(
        name="AGWarning", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=8, leading=10.5, textColor=RED, borderColor=RED, borderWidth=0.6,
        borderPadding=5, backColor=colors.HexColor("#FFF0F0"),
    ))

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setStrokeColor(BRAND)
        canvas.setLineWidth(1)
        canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MID)
        canvas.drawString(18 * mm, 9 * mm, f"AUTOGUARD SCAN DIOS v{version} · Técnico: {author}")
        canvas.drawRightString(192 * mm, 9 * mm, f"Página {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=15 * mm, bottomMargin=20 * mm,
        title="Informe Premium AUTOGUARD SCAN DIOS", author=author,
        subject="Diagnóstico OBD-II con gráficos y plan de acción",
    )
    now = datetime.now()
    dtc_list = list(dtcs)
    history_data = {name: list(samples) for name, samples in (history or {}).items()}
    unique_codes = sorted({str(item.get("code", "")) for item in dtc_list if item.get("code")})

    story = [
        Paragraph("AUTOGUARD SCAN DIOS", styles["AGBrand"]),
        Paragraph("INFORME TÉCNICO PREMIUM DE DIAGNÓSTICO OBD-II", styles["AGSubtitle"]),
    ]

    header_rows = [
        ["Fecha y hora", now.strftime("%d-%m-%Y %H:%M"), "Versión", version],
        ["Cliente", _safe(vehicle.get("cliente")), "Patente", _safe(vehicle.get("patente"))],
        ["Marca", _safe(vehicle.get("marca")), "Modelo / Año", f"{_safe(vehicle.get('modelo'))} / {_safe(vehicle.get('anio'))}"],
        ["VIN", _safe(vehicle.get("vin")), "Kilometraje", _safe(vehicle.get("kilometraje"))],
        ["Motor", _safe(vehicle.get("motor")), "Protocolo", _safe(protocol)],
        ["Técnico", _safe(vehicle.get("tecnico") or author), "Autor aplicación", "Esteban Cortez Richards"],
    ]
    header = Table(header_rows, colWidths=[28 * mm, 57 * mm, 30 * mm, 59 * mm])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C0CC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([header, Paragraph("RESUMEN EJECUTIVO", styles["AGSection"])])

    summary_rows = [
        ["Comunicación ECU", _safe(protocol), "DTC únicos", str(len(unique_codes))],
        ["Sensores registrados", str(len(live_values)), "Gráficos incluidos", str(len(history_data))],
        ["Estado diagnóstico", "Requiere confirmación técnica", "Prioridad", "Según severidad de cada DTC"],
    ]
    summary = Table(summary_rows, colWidths=[34 * mm, 54 * mm, 36 * mm, 50 * mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, MID),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary)

    story.append(Paragraph("CÓDIGOS DTC REGISTRADOS", styles["AGSection"]))
    if dtc_list:
        rows = [["Código", "Estado", "Severidad", "Sistema", "Descripción", "Fabricante"]]
        for item in dtc_list:
            rows.append([
                _safe(item.get("code")), _safe(item.get("status")), _safe(item.get("severity", "Por confirmar")),
                _paragraph(item.get("system", "No identificado"), styles["AGSmall"]),
                _paragraph(item.get("description"), styles["AGSmall"]), _safe(item.get("manufacturer")),
            ])
        table = Table(rows, colWidths=[16 * mm, 19 * mm, 20 * mm, 29 * mm, 61 * mm, 29 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB1BC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5), ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No se registraron códigos DTC durante la sesión.", styles["AGBody"]))

    story.append(Paragraph("DATOS EN VIVO — ÚLTIMA MUESTRA", styles["AGSection"]))
    if live_values:
        live_rows = [["Parámetro", "Valor"]] + [[_safe(key), _safe(value)] for key, value in live_values.items()]
        live_table = Table(live_rows, colWidths=[100 * mm, 74 * mm], repeatRows=1)
        live_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB1BC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(live_table)
    else:
        story.append(Paragraph("No se capturaron datos en vivo.", styles["AGBody"]))

    if history_data:
        story.extend([PageBreak(), Paragraph("GRÁFICOS TÉCNICOS DE LA SESIÓN", styles["AGSection"])])
        story.append(Paragraph(
            "Los gráficos muestran la tendencia temporal de parámetros calculados por la ECU. No representan directamente formas de onda eléctricas de sensores o actuadores.",
            styles["AGBody"],
        ))
        for name, samples in history_data.items():
            story.extend([Spacer(1, 3 * mm), _chart(name, samples), Spacer(1, 2 * mm)])

    if dtc_list:
        story.extend([PageBreak(), Paragraph("PLAN DE ACCIÓN POR CÓDIGO", styles["AGSection"])])
        processed: set[tuple[str, str]] = set()
        for item in dtc_list:
            key = (_safe(item.get("code")), _safe(item.get("manufacturer")))
            if key in processed:
                continue
            processed.add(key)
            severity = _safe(item.get("severity", "Por confirmar"))
            heading = Table([
                [Paragraph(f"{key[0]} · {_safe(item.get('description'))}", styles["AGCode"]), severity]
            ], colWidths=[145 * mm, 29 * mm])
            heading.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.8, BRAND),
                ("TEXTCOLOR", (1, 0), (1, 0), _severity_color(severity)),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"), ("FONTSIZE", (1, 0), (1, 0), 8),
                ("ALIGN", (1, 0), (1, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            blocks = [
                heading,
                Paragraph(f"<b>Sistema:</b> {_safe(item.get('system'))} · <b>Fabricante:</b> {key[1]} · <b>Estado:</b> {_safe(item.get('status'))}", styles["AGBody"]),
                Paragraph("Síntomas probables", styles["AGSection"]), _paragraph(item.get("symptoms"), styles["AGBody"]),
                Paragraph("Causas probables", styles["AGSection"]), _paragraph(item.get("causes"), styles["AGBody"]),
                Paragraph("Proceso de diagnóstico paso a paso", styles["AGSection"]), _paragraph(item.get("steps"), styles["AGBody"]),
                Paragraph("Sensores y parámetros relacionados", styles["AGSection"]), _paragraph(item.get("sensors"), styles["AGBody"]),
                Paragraph("Herramientas y recursos", styles["AGSection"]), _paragraph(item.get("tools"), styles["AGBody"]),
                Paragraph("Validación posterior a la reparación", styles["AGSection"]), _paragraph(item.get("validation"), styles["AGBody"]),
                Spacer(1, 5 * mm),
            ]
            story.append(KeepTogether(blocks[:2]))
            story.extend(blocks[2:])

    story.extend([
        Paragraph("INTERPRETACIÓN RESPONSABLE", styles["AGSection"]),
        Paragraph(
            "Los códigos DTC identifican una condición detectada por el sistema, no necesariamente un componente defectuoso. Antes de reemplazar piezas deben confirmarse alimentaciones, masas, conectores, cableado, condiciones mecánicas, datos en vivo y especificaciones del fabricante. Las funciones OEM, calibraciones y pruebas bidireccionales dependen del vehículo y del equipo compatible.",
            styles["AGWarning"],
        ),
    ])
    if notes.strip():
        story.extend([
            Paragraph("OBSERVACIONES Y CONCLUSIÓN DEL TÉCNICO", styles["AGSection"]),
            Paragraph(notes.replace("\n", "<br/>"), styles["AGBody"]),
        ])

    story.extend([
        Spacer(1, 10 * mm),
        Table(
            [["Técnico responsable", "Recepción del cliente"], [_safe(vehicle.get("tecnico") or author), ""]],
            colWidths=[87 * mm, 87 * mm], rowHeights=[8 * mm, 20 * mm],
            style=TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, MID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
    ])
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output
