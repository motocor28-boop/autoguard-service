from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import APP_NAME, APP_VERSION, AUTHOR, REPORT_DIR
from .dtc_database import DTCDatabase
from .obd import DTCResult, VehicleScan


def _safe(value: object) -> str:
    return str(value if value not in (None, "") else "No disponible")


def generate_pdf_report(
    scan: VehicleScan | None,
    dtcs: Iterable[DTCResult],
    live_data: dict[str, tuple[float | None, str]],
    db: DTCDatabase,
    output_path: Path | None = None,
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = REPORT_DIR / f"Informe_SuperScan_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BrandTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=22,
            textColor=colors.HexColor("#0B74D1"),
            spaceAfter=4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#071B2F"),
            fontSize=13,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallMuted",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#66788A"),
            alignment=TA_LEFT,
        )
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Informe {APP_NAME}",
        author=AUTHOR,
    )

    story = [
        Paragraph("AUTOGUARD", styles["BrandTitle"]),
        Paragraph(f"Informe de diagnóstico automotriz — {APP_NAME}", styles["Heading2"]),
        Paragraph(
            f"Versión {APP_VERSION} · Fecha: {datetime.now():%d-%m-%Y %H:%M:%S}",
            styles["SmallMuted"],
        ),
        Spacer(1, 4 * mm),
    ]

    scan = scan or VehicleScan()
    vehicle_rows = [
        ["VIN", _safe(scan.vin)],
        ["Adaptador", _safe(scan.adapter)],
        ["Protocolo", _safe(scan.protocol_name)],
        ["ATDPN", _safe(scan.protocol_number)],
        ["PIDs disponibles", str(len(scan.supported_pids))],
        ["Estado de monitores", _safe(scan.monitor_raw)],
    ]
    story.append(Paragraph("Identificación y comunicación", styles["Section"]))
    table = Table(vehicle_rows, colWidths=[48 * mm, 125 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F6F9")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#071B2F")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DEE8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)

    story.append(Paragraph("Códigos de diagnóstico", styles["Section"]))
    dtc_rows = [["Código", "Estado", "Descripción"]]
    dtc_list = list(dtcs)
    if not dtc_list:
        dtc_rows.append(["—", "Sin códigos", "No se registraron códigos DTC en la sesión."])
    else:
        for item in dtc_list:
            record = db.lookup(item.code)
            dtc_rows.append([item.code, item.status, Paragraph(record.description, styles["BodyText"])])
    dtc_table = Table(dtc_rows, colWidths=[24 * mm, 43 * mm, 106 * mm], repeatRows=1)
    dtc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#071B2F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5DEE8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(dtc_table)

    story.append(Paragraph("Datos en vivo registrados", styles["Section"]))
    live_rows = [["Parámetro", "Valor", "Unidad"]]
    if not live_data:
        live_rows.append(["—", "Sin datos", "—"])
    else:
        for name, (value, unit) in live_data.items():
            formatted = "No disponible" if value is None else f"{value:.2f}"
            live_rows.append([name, formatted, unit])
    live_table = Table(live_rows, colWidths=[100 * mm, 38 * mm, 35 * mm], repeatRows=1)
    live_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B74D1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5DEE8")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(live_table)
    story.extend(
        [
            Spacer(1, 6 * mm),
            Paragraph(
                "Este informe es un respaldo técnico de la sesión OBD-II. La reparación final debe confirmarse mediante procedimientos, mediciones y especificaciones del fabricante del vehículo.",
                styles["SmallMuted"],
            ),
        ]
    )

    doc.build(story)
    return output_path
