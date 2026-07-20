from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BRAND = colors.HexColor("#E10600")
DARK = colors.HexColor("#151A22")
MID = colors.HexColor("#303846")
LIGHT = colors.HexColor("#EEF1F5")


def _safe(value: object) -> str:
    text = str(value or "No informado").strip()
    return text or "No informado"


def default_report_path() -> Path:
    documents = Path.home() / "Documents" / "AUTOGUARD" / "Informes"
    documents.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return documents / f"Informe_AUTOGUARD_{stamp}.pdf"


def generate_pdf_report(
    output: Path,
    vehicle: Mapping[str, object],
    protocol: str,
    dtcs: Iterable[Mapping[str, object]],
    live_values: Mapping[str, object],
    notes: str = "",
    author: str = "Esteban Cortez Richards",
    version: str = "6.2",
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BrandTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            alignment=TA_CENTER,
            textColor=BRAND,
            spaceAfter=7 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=DARK,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor=MID,
        )
    )

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setStrokeColor(BRAND)
        canvas.setLineWidth(0.7)
        canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MID)
        canvas.drawString(18 * mm, 9 * mm, f"AUTOGUARD SCAN DIOS v{version} · Autor: {author}")
        canvas.drawRightString(192 * mm, 9 * mm, f"Página {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title="Informe AUTOGUARD SCAN DIOS",
        author=author,
    )
    story = [
        Paragraph("AUTOGUARD SCAN DIOS", styles["BrandTitle"]),
        Paragraph("INFORME TÉCNICO DE DIAGNÓSTICO OBD-II", styles["Heading2"]),
        Spacer(1, 2 * mm),
    ]

    now = datetime.now()
    header_rows = [
        ["Fecha", now.strftime("%d-%m-%Y %H:%M"), "Versión", version],
        ["Cliente", _safe(vehicle.get("cliente")), "Patente", _safe(vehicle.get("patente"))],
        ["Marca", _safe(vehicle.get("marca")), "Modelo / Año", f"{_safe(vehicle.get('modelo'))} / {_safe(vehicle.get('anio'))}"],
        ["VIN", _safe(vehicle.get("vin")), "Kilometraje", _safe(vehicle.get("kilometraje"))],
        ["Motor", _safe(vehicle.get("motor")), "Protocolo", _safe(protocol)],
    ]
    header = Table(header_rows, colWidths=[24 * mm, 60 * mm, 27 * mm, 63 * mm])
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C0CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([header, Paragraph("CÓDIGOS DTC REGISTRADOS", styles["Section"])])

    dtc_list = list(dtcs)
    if dtc_list:
        rows = [["Código", "Estado", "Descripción", "Fabricante"]]
        for item in dtc_list:
            rows.append(
                [
                    _safe(item.get("code")),
                    _safe(item.get("status")),
                    Paragraph(_safe(item.get("description")), styles["Small"]),
                    _safe(item.get("manufacturer")),
                ]
            )
        dtc_table = Table(rows, colWidths=[18 * mm, 22 * mm, 97 * mm, 37 * mm], repeatRows=1)
        dtc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB1BC")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(dtc_table)
    else:
        story.append(Paragraph("No se registraron códigos DTC durante la sesión.", styles["BodyText"]))

    story.append(Paragraph("DATOS EN VIVO — ÚLTIMA MUESTRA", styles["Section"]))
    if live_values:
        live_rows = [["Parámetro", "Valor"]]
        for key, value in live_values.items():
            live_rows.append([_safe(key), _safe(value)])
        live_table = Table(live_rows, colWidths=[90 * mm, 84 * mm], repeatRows=1)
        live_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB1BC")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(live_table)
    else:
        story.append(Paragraph("No se capturaron datos en vivo.", styles["BodyText"]))

    story.extend(
        [
            Paragraph("INTERPRETACIÓN Y ALCANCE", styles["Section"]),
            Paragraph(
                "El diagnóstico es preliminar y debe confirmarse con inspección física, mediciones, diagramas y especificaciones OEM. "
                "No se recomienda sustituir componentes basándose únicamente en un código DTC. La señal eléctrica directa de CKP, CMP, "
                "inyectores, bobinas, CAN o PWM requiere un osciloscopio físico y sondas adecuadas; ELM327 entrega telemetría calculada por la ECU.",
                styles["BodyText"],
            ),
        ]
    )
    if notes.strip():
        story.extend(
            [
                Paragraph("OBSERVACIONES DEL TÉCNICO", styles["Section"]),
                Paragraph(notes.replace("\n", "<br/>"), styles["BodyText"]),
            ]
        )

    story.extend(
        [
            Spacer(1, 10 * mm),
            Table(
                [["Técnico responsable", "Recepción del cliente"], [author, ""]],
                colWidths=[87 * mm, 87 * mm],
                rowHeights=[8 * mm, 18 * mm],
                style=TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, MID),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
        ]
    )

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output
