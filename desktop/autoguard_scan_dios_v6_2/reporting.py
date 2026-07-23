from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = colors.HexColor("#FF6900")
BRAND_LIGHT = colors.HexColor("#FFF0E5")
BRAND_DARK = colors.HexColor("#B74600")
DARK = colors.HexColor("#121A23")
DARK_2 = colors.HexColor("#202B36")
MID = colors.HexColor("#465462")
LIGHT = colors.HexColor("#EDF1F5")
VERY_LIGHT = colors.HexColor("#F8F9FB")
GREEN = colors.HexColor("#258B53")
BLUE = colors.HexColor("#2677A8")
RED = colors.HexColor("#C92E35")
YELLOW = colors.HexColor("#D38A00")
WHITE = colors.white

DEFAULT_PHONE = "+56 9 7748 2821"
DEFAULT_EMAIL = "autoguard.chile.servicios@outlook.com"
DEFAULT_AREA = "ANTOFAGASTA Y ALREDEDORES"
DEFAULT_TAGLINE = "Diagnóstico responsable: comprobar antes de reemplazar."


def _safe(value: object, fallback: str = "No informado") -> str:
    text = str(value or "").strip()
    return text or fallback


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def _paragraph(text: object, style) -> Paragraph:
    return Paragraph(_safe(text).replace("\n", "<br/>"), style)


def _resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def _split_steps(value: object) -> list[str]:
    """Normaliza procedimientos de la base offline en pasos imprimibles."""
    text = str(value or "").replace("\r", "\n").strip()
    if not text:
        return ["Confirmar el procedimiento específico con la documentación OEM del vehículo."]

    raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(raw_lines) <= 1:
        raw_lines = [
            part.strip()
            for part in re.split(r"(?=(?:\d{1,2}[\.)]|[-•])\s+)", text)
            if part.strip()
        ]

    cleaned: list[str] = []
    for line in raw_lines:
        line = re.sub(r"^(?:\d{1,2}[\.)]|[-•])\s*", "", line).strip()
        if line and line not in cleaned:
            cleaned.append(line)
    return cleaned or [text]


def _split_items(value: object) -> list[str]:
    text = str(value or "").replace("\r", "\n").strip()
    if not text:
        return []
    pieces = re.split(r"\n+|;\s*|(?<=[\.])\s+(?=[A-ZÁÉÍÓÚÑ])", text)
    items: list[str] = []
    for piece in pieces:
        clean = re.sub(r"^[-•\d\.\)\s]+", "", piece).strip(" .")
        if clean and clean not in items:
            items.append(clean)
    return items


def _first_sentence(value: object, fallback: str) -> str:
    text = _clean_text(value)
    if not text:
        return fallback
    sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    return sentence[:220]


def default_report_path() -> Path:
    documents = Path.home() / "Documents" / "AUTOGUARD" / "Informes"
    documents.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return documents / f"Informe_TECNICO_PREMIUM_AUTOGUARD_{stamp}.pdf"


def _severity_color(severity: str):
    value = severity.casefold()
    if "alta" in value or "crítica" in value or "critica" in value:
        return RED
    if "media" in value:
        return YELLOW
    return GREEN


def _priority_from_dtcs(dtcs: Sequence[Mapping[str, object]]) -> str:
    severities = " ".join(_safe(item.get("severity"), "").casefold() for item in dtcs)
    if "crítica" in severities or "critica" in severities or "alta" in severities:
        return "Alta"
    if dtcs:
        return "Media-alta"
    return "Baja"


def _report_summary(dtcs: Sequence[Mapping[str, object]]) -> str:
    codes = [str(item.get("code", "")).strip() for item in dtcs if item.get("code")]
    if not codes:
        return "Escaneo OBD-II, análisis de datos en vivo y verificación de ausencia de códigos activos"
    joined = " y ".join(codes[:2]) if len(codes) <= 2 else ", ".join(codes[:3]) + " y otros"
    return f"Análisis de códigos {joined}, correlación de datos en vivo y procedimiento técnico paso a paso"


def _cross_code_criterion(dtcs: Sequence[Mapping[str, object]]) -> str:
    if not dtcs:
        return "La ECU no informó códigos activos. Se recomienda conservar el registro y revisar monitores OBD-II antes de cerrar el diagnóstico."
    if len(dtcs) == 1:
        code = _safe(dtcs[0].get("code"))
        return (
            f"El código {code} orienta el diagnóstico, pero no confirma por sí solo un componente defectuoso. "
            "La causa debe demostrarse mediante inspección, mediciones, datos en vivo y especificaciones OEM."
        )
    systems = sorted({_safe(item.get("system"), "Sistema no identificado") for item in dtcs})
    return (
        "La combinación de códigos obliga a buscar primero causas comunes: alimentación, masa, conectores, "
        "admisión, mezcla, red de comunicación o condiciones mecánicas. Correlacionar los sistemas "
        f"{', '.join(systems[:3])} antes de autorizar reemplazos simultáneos."
    )


def _review_suggestions(item: Mapping[str, object]) -> list[str]:
    code = _safe(item.get("code"), "").upper()
    description = _clean_text(item.get("description")).casefold()
    system = _clean_text(item.get("system")).casefold()
    combined = f"{code} {description} {system} {_clean_text(item.get('causes')).casefold()}"

    suggestions = [
        "Registrar el estado del DTC, freeze frame, kilometraje y condiciones exactas en que apareció la falla.",
        "Realizar inspección visual de conectores, terminales, mazos, mangueras, fijaciones, fugas y componentes intervenidos anteriormente.",
    ]

    if code.startswith("U") or "comunicación" in combined or "can" in combined:
        suggestions.extend([
            "Comprobar batería, voltaje durante arranque, fusibles, alimentaciones y masas de los módulos involucrados.",
            "Inspeccionar CAN High/Low, empalmes, humedad, corrosión y resistencia de terminación conforme al diagrama OEM.",
            "Confirmar qué módulo deja de responder antes de condenar una ECU o sensor de red.",
        ])
    elif code.startswith("C") or any(word in combined for word in ("abs", "chasis", "dirección", "rueda")):
        suggestions.extend([
            "Comparar velocidades de rueda, ángulo de dirección y sensores de estabilidad durante una prueba controlada.",
            "Revisar neumáticos, rodamientos, reluctores, conectores y cableado expuesto a movimiento o contaminación.",
            "Ejecutar calibraciones únicamente después de confirmar integridad mecánica y eléctrica.",
        ])
    elif code.startswith("B"):
        suggestions.extend([
            "Verificar fusibles, alimentación, masa, interruptores y actuadores del sistema de carrocería afectado.",
            "Comparar estados de entradas y salidas en datos en vivo antes de desmontar módulos o paneles.",
        ])
    else:
        if any(word in combined for word in ("maf", "masa de aire", "p010", "admisión")):
            suggestions.extend([
                "Revisar filtro de aire, caja, ductos, abrazaderas, resonadores, PCV y posibles fugas posteriores al MAF.",
                "Inspeccionar y, si corresponde, limpiar el MAF exclusivamente con producto específico, sin tocar el elemento sensible.",
                "Comparar MAF, MAP, RPM, carga calculada, STFT y LTFT en ralentí y a régimen estable.",
            ])
        if any(word in combined for word in ("oxígeno", "oxygen", "o2", "p2a", "lambda")):
            suggestions.extend([
                "Revisar fugas de escape antes del sensor, cableado afectado por calor y alimentación del calentador.",
                "Corregir primero mezcla, misfire, admisión o combustible antes de reemplazar el sensor de oxígeno.",
                "Evaluar la respuesta rica/pobre y compararla con el criterio OEM del motor.",
            ])
        if any(word in combined for word in ("combustible", "fuel", "riel", "inyector")):
            suggestions.extend([
                "Medir presión y caudal de combustible bajo las condiciones del freeze frame.",
                "Revisar alimentación de bomba, filtro, regulador, inyectores y posibles restricciones o fugas.",
            ])
        if any(word in combined for word in ("misfire", "encendido", "p030")):
            suggestions.extend([
                "Revisar contadores de misfire, bujías, bobinas, inyectores, compresión y sincronización.",
                "No mantener el motor bajo carga cuando la MIL parpadea, por riesgo de daño al catalítico.",
            ])
        if any(word in combined for word in ("presión de aceite", "oil pressure", "p052")):
            suggestions.extend([
                "Verificar nivel, viscosidad y estado del aceite antes de intervenir el sensor.",
                "Si existe testigo rojo, ruido o lectura anormal, medir presión real con manómetro mecánico y comparar con OEM.",
                "No reemplazar el interruptor para ocultar una condición real de baja presión.",
            ])
        if any(word in combined for word in ("temperatura", "refrigerante", "termostato", "p0128")):
            suggestions.extend([
                "Comparar ECT, IAT y temperatura ambiente con motor frío y durante el calentamiento.",
                "Revisar nivel, purga, termostato, ventilador, fugas y coherencia de la señal antes de sustituir sensores.",
            ])
        if any(word in combined for word in ("catalizador", "catalyst", "p0420")):
            suggestions.extend([
                "Resolver primero misfire, mezcla rica/pobre, consumo de aceite y fugas de escape.",
                "Comparar sensores anterior y posterior, temperatura y monitores antes de autorizar catalítico.",
            ])

    suggestions.extend([
        "Verificar alimentación, masa, señal y continuidad con el diagrama eléctrico del vehículo exacto.",
        "Reparar únicamente la causa confirmada, borrar códigos después de guardar evidencia y repetir la prueba bajo las condiciones originales.",
    ])

    unique: list[str] = []
    for suggestion in suggestions:
        if suggestion not in unique:
            unique.append(suggestion)
    return unique[:10]


def _repair_recommendation(item: Mapping[str, object]) -> str:
    code = _safe(item.get("code"))
    validation = _clean_text(item.get("validation"))
    return (
        f"Para {code}, no autorizar repuestos por el código solamente. Corregir la causa demostrada, "
        "restablecer conectores y cableado, completar reaprendizajes cuando corresponda y validar con datos en vivo. "
        + (validation if validation else "Confirmar que el DTC no reaparezca después de una prueba controlada.")
    )


def _section_heading(title: str, styles) -> Table:
    table = Table([[Paragraph(title, styles["AGSectionText"])]], colWidths=[174 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("LINEBELOW", (0, 0), (-1, -1), 4, BRAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _callout(label: str, text: str, styles, accent=BRAND, background=BRAND_LIGHT) -> Table:
    content = Paragraph(f"<b>{label}:</b> {text}", styles["AGBody"])
    table = Table([["", content]], colWidths=[4 * mm, 170 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), accent),
        ("BACKGROUND", (1, 0), (1, 0), background),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("RIGHTPADDING", (1, 0), (1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _bullet_table(items: Sequence[str], styles, accent=BRAND) -> Table:
    rows = [[Paragraph("•", styles["AGBulletMark"]), Paragraph(item, styles["AGBody"])] for item in items]
    table = Table(rows, colWidths=[7 * mm, 167 * mm])
    table.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (0, -1), accent),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _numbered_steps_table(steps: Sequence[str], styles) -> LongTable:
    rows: list[list[object]] = []
    for index, step in enumerate(steps, start=1):
        rows.append([
            Paragraph(str(index), styles["AGStepNumber"]),
            Paragraph(step, styles["AGStep"]),
        ])
    table = LongTable(rows, colWidths=[9 * mm, 165 * mm], repeatRows=0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND),
        ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (1, 0), (1, -1), 0.25, colors.HexColor("#CFD5DB")),
        ("LEFTPADDING", (0, 0), (0, -1), 2),
        ("RIGHTPADDING", (0, 0), (0, -1), 2),
        ("LEFTPADDING", (1, 0), (1, -1), 7),
        ("RIGHTPADDING", (1, 0), (1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _chart_interpretation(title: str, samples: Sequence[tuple[float, float]]) -> str:
    if not samples:
        return "No existen muestras suficientes para interpretar la tendencia."
    values = [float(value) for _timestamp, value in samples]
    minimum = min(values)
    maximum = max(values)
    average = mean(values)
    spread = maximum - minimum
    if abs(spread) < max(abs(average) * 0.01, 0.05):
        behavior = "La señal permaneció estable durante la captura."
    elif spread > max(abs(average) * 0.45, 10):
        behavior = "La señal presentó una variación amplia; correlacionar con carga, RPM y condición de prueba."
    else:
        behavior = "La señal mostró variación moderada y debe compararse con el rango OEM."
    return f"{title}: mínimo {minimum:.2f}, promedio {average:.2f}, máximo {maximum:.2f}. {behavior}"


def _chart(
    title: str,
    samples: list[tuple[float, float]],
    width: float = 174 * mm,
    height: float = 78 * mm,
) -> Drawing:
    """Gráfico vectorial HD: mantiene nitidez al ampliar o imprimir."""
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=WHITE, strokeColor=colors.HexColor("#9AA7B3"), strokeWidth=0.7))
    drawing.add(Rect(0, height - 13 * mm, width, 13 * mm, fillColor=DARK, strokeColor=DARK))
    drawing.add(String(8 * mm, height - 8.5 * mm, title, fontName="Helvetica-Bold", fontSize=10, fillColor=WHITE))
    drawing.add(String(width - 45 * mm, height - 8.5 * mm, "GRÁFICO VECTORIAL HD", fontName="Helvetica-Bold", fontSize=7, fillColor=BRAND))

    if not samples:
        drawing.add(String(12 * mm, height / 2, "Sin muestras", fontName="Helvetica", fontSize=9, fillColor=MID))
        return drawing

    if len(samples) > 360:
        step = max(1, len(samples) // 360)
        samples = samples[::step]

    start = samples[0][0]
    points = [(float(timestamp - start), float(value)) for timestamp, value in samples]
    values = [point[1] for point in points]
    minimum = min(values)
    maximum = max(values)
    average = mean(values)
    span = maximum - minimum
    margin = max(span * 0.12, abs(average) * 0.025, 0.5)

    chart = LinePlot()
    chart.x = 18 * mm
    chart.y = 15 * mm
    chart.width = width - 29 * mm
    chart.height = height - 37 * mm
    chart.data = [points]
    chart.joinedLines = 1
    chart.lines[0].strokeColor = BRAND
    chart.lines[0].strokeWidth = 2.2
    chart.xValueAxis.valueMin = min(point[0] for point in points)
    chart.xValueAxis.valueMax = max(max(point[0] for point in points), chart.xValueAxis.valueMin + 1)
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
    chart.xValueAxis.gridStrokeColor = colors.HexColor("#D4DAE0")
    chart.yValueAxis.gridStrokeColor = colors.HexColor("#D4DAE0")
    chart.xValueAxis.gridStrokeWidth = 0.35
    chart.yValueAxis.gridStrokeWidth = 0.35
    drawing.add(chart)

    drawing.add(String(6 * mm, 5 * mm, f"Mín {minimum:.2f}", fontName="Helvetica-Bold", fontSize=7, fillColor=BLUE))
    drawing.add(String(63 * mm, 5 * mm, f"Prom {average:.2f}", fontName="Helvetica-Bold", fontSize=7, fillColor=GREEN))
    drawing.add(String(119 * mm, 5 * mm, f"Máx {maximum:.2f}", fontName="Helvetica-Bold", fontSize=7, fillColor=RED))
    drawing.add(String(width - 31 * mm, 5 * mm, "Tiempo [s]", fontName="Helvetica", fontSize=7, fillColor=MID))
    return drawing


def _build_work_plan(dtcs: Sequence[Mapping[str, object]], styles) -> LongTable:
    tasks: list[tuple[str, str, str, str]] = [
        (
            "Guardar DTC, estado y freeze frame",
            "Scanner AUTOGUARD",
            "Evidencia completa conservada",
            "No borrar códigos; repetir lectura y registrar condiciones",
        ),
        (
            "Revisar batería, alimentación, masas, conectores y mazos",
            "Multímetro / inspección",
            "Voltajes y conexiones conformes",
            "Reparar alimentación, masa, terminal o cableado",
        ),
    ]

    for item in dtcs:
        code = _safe(item.get("code"))
        suggestions = _review_suggestions(item)
        activity = suggestions[2] if len(suggestions) > 2 else suggestions[0]
        tool = _first_sentence(item.get("tools"), "Scanner, multímetro y documentación OEM")
        expected = _first_sentence(item.get("validation"), "Lectura coherente y condición corregida")
        failure = f"Continuar diagnóstico de {code}; no sustituir componentes sin confirmar la causa"
        tasks.append((f"{code}: {activity}", tool, expected, failure))

    tasks.extend([
        (
            "Correlacionar datos en vivo y gráficos",
            "Scanner / gráficos HD",
            "Señales coherentes con carga y condición",
            "Ampliar prueba, comparar sensores y consultar rango OEM",
        ),
        (
            "Borrar códigos y ejecutar validación final",
            "Scanner / prueba de ruta",
            "Sin DTC activos o pendientes relacionados",
            "Recuperar freeze frame nuevo y continuar causa raíz",
        ),
    ])

    rows: list[list[object]] = [["ORDEN", "ACTIVIDAD", "HERRAMIENTA", "RESULTADO ESPERADO", "ACCIÓN SI FALLA"]]
    for index, (activity, tool, expected, failure) in enumerate(tasks[:9], start=1):
        rows.append([
            str(index),
            Paragraph(activity, styles["AGSmall"]),
            Paragraph(tool, styles["AGSmall"]),
            Paragraph(expected, styles["AGSmall"]),
            Paragraph(failure, styles["AGSmall"]),
        ])
    table = LongTable(rows, colWidths=[13 * mm, 47 * mm, 35 * mm, 37 * mm, 42 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("TEXTCOLOR", (0, 1), (0, -1), BRAND),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB1BC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [VERY_LIGHT, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _delivery_checklist(dtcs: Sequence[Mapping[str, object]]) -> list[str]:
    checklist = [
        "Datos del vehículo, VIN, kilometraje y condiciones del diagnóstico registrados.",
        "Códigos, estado y freeze frame guardados antes de borrar información.",
        "Batería, alimentaciones, masas, conectores y cableado verificados.",
        "Fugas, mangueras, fijaciones y componentes relacionados inspeccionados.",
        "Datos en vivo y gráficos comparados con la condición de falla.",
    ]
    for item in dtcs[:4]:
        code = _safe(item.get("code"))
        checklist.append(f"{code}: causa raíz confirmada mediante medición o prueba técnica.")
    checklist.extend([
        "Reparación validada bajo las condiciones del freeze frame.",
        "Códigos borrados únicamente después de conservar la evidencia.",
        "Prueba de ruta o ciclo funcional realizado sin síntomas críticos.",
        "Reescaneo final sin DTC activos o pendientes relacionados.",
    ])
    return checklist[:11]


def _technical_conclusion(dtcs: Sequence[Mapping[str, object]], notes: str) -> str:
    if notes.strip():
        return notes.strip()
    if not dtcs:
        return (
            "Durante la sesión no se registraron códigos activos. La ausencia de DTC no descarta fallas intermitentes, "
            "mecánicas o de módulos no accesibles por el adaptador. Se recomienda completar monitores, revisar datos en vivo "
            "y repetir el escaneo si reaparece el síntoma."
        )
    codes = ", ".join(_safe(item.get("code")) for item in dtcs)
    return (
        f"Se registraron los códigos {codes}. Los DTC identifican condiciones detectadas por la ECU, pero no autorizan por sí "
        "solos el reemplazo de componentes. La reparación debe concentrarse en la causa confirmada mediante inspección, "
        "mediciones, correlación de sensores, documentación OEM y validación posterior."
    )


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
    """Genera un informe técnico tipo scanner y subinformes de reparación.

    `version` se conserva únicamente por compatibilidad con versiones anteriores
    de la aplicación y no se imprime en el documento.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    dtc_list = list(dtcs)
    history_data = {name: list(samples) for name, samples in (history or {}).items() if list(samples)}
    now = datetime.now()
    report_id = now.strftime("AG-%Y%m%d-%H%M%S")
    priority = _priority_from_dtcs(dtc_list)
    condition = "Diagnóstico pendiente de pruebas y validación" if dtc_list else "Sin códigos activos"
    phone = _safe(vehicle.get("contact_phone"), DEFAULT_PHONE)
    email = _safe(vehicle.get("contact_email"), DEFAULT_EMAIL)
    service_area = _safe(vehicle.get("service_area"), DEFAULT_AREA)
    report_type = _safe(vehicle.get("report_type"), "Diagnóstico técnico tipo scanner")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AGTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=23, alignment=TA_CENTER, textColor=DARK, spaceAfter=1.5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AGSubtitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=14, alignment=TA_CENTER, textColor=BRAND, spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AGLead", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.7, leading=11, alignment=TA_CENTER, textColor=MID, spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AGSectionText", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=15, leading=17, textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name="AGBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.5, leading=11.2, textColor=DARK, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="AGSmall", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=7.2, leading=9, textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name="AGFine", parent=styles["BodyText"], fontName="Helvetica-Oblique",
        fontSize=6.5, leading=8, textColor=MID, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="AGCode", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=13, leading=15, textColor=RED,
    ))
    styles.add(ParagraphStyle(
        name="AGStep", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.3, leading=10.5, textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name="AGStepNumber", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=9, leading=11, alignment=TA_CENTER, textColor=WHITE,
    ))
    styles.add(ParagraphStyle(
        name="AGBulletMark", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=10, leading=11, textColor=BRAND,
    ))
    styles.add(ParagraphStyle(
        name="AGCardLabel", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=7, leading=8, alignment=TA_CENTER, textColor=BRAND,
    ))
    styles.add(ParagraphStyle(
        name="AGCardValue", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=9, leading=10, alignment=TA_CENTER, textColor=WHITE,
    ))

    page_width, page_height = A4
    logo_path = _resource_path("autoguard.png")

    def page_header_footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFillColor(DARK)
        canvas.rect(14 * mm, page_height - 25 * mm, page_width - 28 * mm, 17 * mm, fill=1, stroke=0)
        if logo_path.is_file():
            try:
                canvas.drawImage(
                    str(logo_path), 18 * mm, page_height - 23.5 * mm,
                    width=57 * mm, height=14 * mm, preserveAspectRatio=True, mask="auto",
                )
            except Exception:
                canvas.setFillColor(WHITE)
                canvas.setFont("Helvetica-Bold", 13)
                canvas.drawString(19 * mm, page_height - 18 * mm, "AUTOGUARD SERVICE")
        else:
            canvas.setFillColor(WHITE)
            canvas.setFont("Helvetica-Bold", 13)
            canvas.drawString(19 * mm, page_height - 18 * mm, "AUTOGUARD SERVICE")

        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawRightString(page_width - 18 * mm, page_height - 15 * mm, "INFORME TÉCNICO TIPO SCANNER")
        canvas.setFont("Helvetica", 7.2)
        vehicle_line = f"{_safe(vehicle.get('marca'))} {_safe(vehicle.get('modelo'))} {_safe(vehicle.get('anio'))} · Diagnóstico y reparación"
        canvas.drawRightString(page_width - 18 * mm, page_height - 20 * mm, vehicle_line)

        canvas.setStrokeColor(BRAND)
        canvas.setLineWidth(0.8)
        canvas.line(15 * mm, 14 * mm, page_width - 15 * mm, 14 * mm)
        canvas.setFillColor(MID)
        canvas.setFont("Helvetica", 6.8)
        canvas.drawString(15 * mm, 9 * mm, f"AutoGuard Service  |  {phone}  |  {email}")
        canvas.drawRightString(page_width - 15 * mm, 9 * mm, f"Página {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output), pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=30 * mm, bottomMargin=20 * mm,
        title="Informe técnico de diagnóstico y reparación AUTOGUARD",
        author=author,
        subject="Diagnóstico OBD-II, gráficos HD y procedimientos de reparación",
    )

    story: list[object] = [
        Paragraph("INFORME TÉCNICO DE DIAGNÓSTICO Y<br/>REPARACIÓN", styles["AGTitle"]),
        Paragraph(
            f"FORMATO SCANNER PREMIUM - {_safe(vehicle.get('marca')).upper()} {_safe(vehicle.get('modelo')).upper()} {_safe(vehicle.get('anio')).upper()}",
            styles["AGSubtitle"],
        ),
        Paragraph(_report_summary(dtc_list), styles["AGLead"]),
    ]

    header_rows = [
        ["N° DE INFORME", report_id, "FECHA", now.strftime("%d-%m-%Y")],
        ["MARCA", _safe(vehicle.get("marca")), "MODELO / AÑO", f"{_safe(vehicle.get('modelo'))} / {_safe(vehicle.get('anio'))}"],
        ["MOTOR", _safe(vehicle.get("motor")), "KILOMETRAJE", _safe(vehicle.get("kilometraje"))],
        ["PATENTE / VIN", f"{_safe(vehicle.get('patente'))} / {_safe(vehicle.get('vin'))}", "CLIENTE", _safe(vehicle.get("cliente"))],
        ["TIPO DE INFORME", report_type, "PRIORIDAD", priority],
        ["PROTOCOLO", _safe(protocol), "TÉCNICO", _safe(vehicle.get("tecnico") or author)],
    ]
    header_table = Table(header_rows, colWidths=[30 * mm, 55 * mm, 31 * mm, 58 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.4),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B6C0CA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([
        header_table,
        Spacer(1, 2.5 * mm),
        _callout(
            "ALCANCE",
            "Informe generado a partir del escaneo OBD-II, datos en vivo, historial de la sesión y base técnica offline. "
            "La identificación final de repuestos, conectores, valores, torques y secuencias debe confirmarse con VIN, código de motor y manual OEM.",
            styles,
        ),
        Spacer(1, 2.5 * mm),
    ])

    codes_text = " / ".join(_safe(item.get("code")) for item in dtc_list) if dtc_list else "SIN CÓDIGOS ACTIVOS"
    system_text = ", ".join(sorted({_safe(item.get("system"), "No identificado") for item in dtc_list})) if dtc_list else "Monitores y datos en vivo"
    cards = Table([
        [Paragraph("CÓDIGOS REGISTRADOS", styles["AGCardLabel"]), Paragraph("SISTEMAS ASOCIADOS", styles["AGCardLabel"]), Paragraph("CONDICIÓN", styles["AGCardLabel"])],
        [Paragraph(codes_text, styles["AGCardValue"]), Paragraph(system_text, styles["AGCardValue"]), Paragraph(condition, styles["AGCardValue"])],
    ], colWidths=[58 * mm, 58 * mm, 58 * mm])
    cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#394652")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#394652")),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
    ]))
    story.extend([
        cards,
        Spacer(1, 3 * mm),
        Paragraph(f"AUTOGUARD SERVICE - {service_area}", styles["AGSubtitle"]),
        Paragraph(DEFAULT_TAGLINE, styles["AGFine"]),
        PageBreak(),
        _section_heading("1. ANTECEDENTES Y CÓDIGOS REGISTRADOS", styles),
        Spacer(1, 3 * mm),
    ])

    if dtc_list:
        code_rows: list[list[object]] = [["CÓDIGO", "DESCRIPCIÓN", "CAUSAS PROBABLES", "EFECTOS POSIBLES"]]
        for item in dtc_list:
            code_rows.append([
                Paragraph(_safe(item.get("code")), styles["AGCode"]),
                Paragraph(_safe(item.get("description")), styles["AGSmall"]),
                Paragraph(_safe(item.get("causes")), styles["AGSmall"]),
                Paragraph(_safe(item.get("symptoms")), styles["AGSmall"]),
            ])
        code_table = LongTable(code_rows, colWidths=[18 * mm, 55 * mm, 58 * mm, 43 * mm], repeatRows=1)
        code_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [VERY_LIGHT, LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B6C0CA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([
            code_table,
            Spacer(1, 3 * mm),
            _callout("CRITERIO TÉCNICO", _cross_code_criterion(dtc_list), styles, accent=BLUE, background=colors.HexColor("#EAF5FB")),
            Spacer(1, 3 * mm),
            _callout(
                "PRIORIDAD",
                "No se recomienda cambiar simultáneamente sensores, actuadores o módulos. Revisar primero causas comunes, "
                "confirmar cada circuito y reparar fugas, alimentación, masas o contaminación demostradas.",
                styles,
                accent=BRAND,
                background=BRAND_LIGHT,
            ),
        ])
    else:
        story.extend([
            _callout(
                "RESULTADO DEL ESCANEO",
                "SIN CÓDIGOS ACTIVOS. La ECU no informó DTC confirmados durante la sesión. Revisar códigos pendientes, permanentes, monitores y síntomas intermitentes antes de cerrar el diagnóstico.",
                styles,
                accent=GREEN,
                background=colors.HexColor("#EAF7EF"),
            ),
        ])

    story.extend([
        Spacer(1, 5 * mm),
        _section_heading("2. SISTEMAS, COMPONENTES Y REVISIONES SUGERIDAS", styles),
        Spacer(1, 3 * mm),
    ])

    if dtc_list:
        systems_rows: list[list[object]] = [["CÓDIGO", "SISTEMA / COMPONENTE", "SENSORES RELACIONADOS", "SUGERENCIA DE REVISIÓN"]]
        for item in dtc_list:
            suggestions = _review_suggestions(item)
            systems_rows.append([
                Paragraph(_safe(item.get("code")), styles["AGCode"]),
                Paragraph(_safe(item.get("system")), styles["AGSmall"]),
                Paragraph(_safe(item.get("sensors")), styles["AGSmall"]),
                Paragraph(suggestions[2] if len(suggestions) > 2 else suggestions[0], styles["AGSmall"]),
            ])
        systems_table = LongTable(systems_rows, colWidths=[18 * mm, 42 * mm, 55 * mm, 59 * mm], repeatRows=1)
        systems_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.2),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B6C0CA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([
            systems_table,
            Spacer(1, 3 * mm),
            _callout(
                "CONFIRMACIÓN OBLIGATORIA",
                "Antes de comprar repuestos, confirmar número de pieza por VIN, código de motor, forma del conector, terminales, rango de aplicación y especificaciones del fabricante.",
                styles,
                accent=BLUE,
                background=colors.HexColor("#EAF5FB"),
            ),
        ])

    if live_values:
        story.extend([
            Spacer(1, 5 * mm),
            _section_heading("3. DATOS EN VIVO - ÚLTIMA MUESTRA", styles),
            Spacer(1, 3 * mm),
        ])
        live_rows: list[list[object]] = [["PARÁMETRO", "VALOR", "INTERPRETACIÓN"]]
        for key, value in live_values.items():
            live_rows.append([
                Paragraph(_safe(key), styles["AGSmall"]),
                Paragraph(_safe(value), styles["AGSmall"]),
                Paragraph("Comparar con el rango OEM y correlacionar con carga, RPM y condición de prueba.", styles["AGSmall"]),
            ])
        live_table = LongTable(live_rows, colWidths=[73 * mm, 35 * mm, 66 * mm], repeatRows=1)
        live_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [VERY_LIGHT, LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B6C0CA")),
            ("FONTSIZE", (0, 0), (-1, -1), 7.2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(live_table)

    if history_data:
        story.extend([
            PageBreak(),
            _section_heading("4. GRÁFICOS VECTORIALES HD DE LA SESIÓN", styles),
            Spacer(1, 2 * mm),
            _callout(
                "INTERPRETACIÓN",
                "Los gráficos representan parámetros calculados y transmitidos por la ECU. No sustituyen la medición eléctrica directa con osciloscopio físico cuando se requiere analizar CKP, CMP, inyectores, bobinas, PWM o red CAN.",
                styles,
                accent=BLUE,
                background=colors.HexColor("#EAF5FB"),
            ),
            Spacer(1, 3 * mm),
        ])
        for chart_index, (name, samples) in enumerate(history_data.items(), start=1):
            story.extend([
                _chart(name, samples),
                Spacer(1, 1.5 * mm),
                _callout("LECTURA TÉCNICA", _chart_interpretation(name, samples), styles, accent=BRAND, background=VERY_LIGHT),
                Spacer(1, 4 * mm),
            ])
            if chart_index % 2 == 0 and chart_index < len(history_data):
                story.append(PageBreak())

    section_number = 5
    for item in dtc_list:
        code = _safe(item.get("code"))
        description = _safe(item.get("description"))
        suggestions = _review_suggestions(item)
        steps = _split_steps(item.get("steps"))
        story.extend([
            PageBreak(),
            _section_heading(f"{section_number}. DIAGNÓSTICO Y REPARACIÓN DEL CÓDIGO {code}", styles),
            Spacer(1, 3 * mm),
            _callout(
                "OBJETIVO",
                f"Determinar por qué la ECU registró {code} y confirmar la causa raíz. El código no demuestra por sí solo que el componente descrito esté defectuoso.",
                styles,
                accent=BLUE,
                background=colors.HexColor("#EAF5FB"),
            ),
            Spacer(1, 3 * mm),
            Paragraph(f"<b>Descripción técnica:</b> {description}", styles["AGBody"]),
            Spacer(1, 2 * mm),
            Paragraph("<b>Síntomas y efectos posibles</b>", styles["AGBody"]),
            _bullet_table(_split_items(item.get("symptoms")) or ["La condición puede presentarse sin síntomas evidentes."], styles),
            Spacer(1, 2 * mm),
            Paragraph("<b>Causas probables</b>", styles["AGBody"]),
            _bullet_table(_split_items(item.get("causes")) or ["Requiere confirmación mediante pruebas del sistema."], styles),
            Spacer(1, 2 * mm),
            Paragraph("<b>Sugerencias de revisión antes de reparar</b>", styles["AGBody"]),
            _numbered_steps_table(suggestions, styles),
            Spacer(1, 3 * mm),
            Paragraph("<b>Procedimiento de diagnóstico y solución paso a paso</b>", styles["AGBody"]),
            _numbered_steps_table(steps, styles),
            Spacer(1, 3 * mm),
            _callout("DECISIÓN TÉCNICA", _repair_recommendation(item), styles, accent=RED, background=colors.HexColor("#FBECEC")),
            Spacer(1, 3 * mm),
            Paragraph("<b>Herramientas y recursos recomendados</b>", styles["AGBody"]),
            _bullet_table(_split_items(item.get("tools")) or ["Scanner, multímetro y documentación OEM."], styles),
            Spacer(1, 2 * mm),
            Paragraph("<b>Validación posterior a la reparación</b>", styles["AGBody"]),
            _callout(
                "VALIDAR",
                _safe(item.get("validation"), "Borrar códigos después de registrar evidencia, repetir la condición original y confirmar que el DTC no reaparezca."),
                styles,
                accent=GREEN,
                background=colors.HexColor("#EAF7EF"),
            ),
        ])
        section_number += 1

    story.extend([
        PageBreak(),
        _section_heading(f"{section_number}. PLAN DE TRABAJO RECOMENDADO", styles),
        Spacer(1, 3 * mm),
        _build_work_plan(dtc_list, styles),
        Spacer(1, 5 * mm),
        _section_heading(f"{section_number + 1}. CHECKLIST DE ENTREGA", styles),
        Spacer(1, 3 * mm),
    ])

    checklist_rows = [[Paragraph("[  ]", styles["AGCode"]), Paragraph(item, styles["AGBody"])] for item in _delivery_checklist(dtc_list)]
    checklist_table = LongTable(checklist_rows, colWidths=[12 * mm, 162 * mm])
    checklist_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), DARK_2),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [VERY_LIGHT, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B6C0CA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    conclusion = _technical_conclusion(dtc_list, notes)
    recommendation = (
        "Priorizar condiciones de seguridad y fallas capaces de producir daño mecánico o al catalítico. "
        "Después, reparar la causa raíz según los datos en vivo, mediciones y pruebas del sistema. "
        "Autorizar repuestos únicamente con confirmación técnica y número de pieza por VIN."
    )
    story.extend([
        checklist_table,
        Spacer(1, 5 * mm),
        _section_heading(f"{section_number + 2}. CONCLUSIÓN TÉCNICA", styles),
        Spacer(1, 3 * mm),
        Paragraph(conclusion.replace("\n", "<br/>"), styles["AGBody"]),
        Spacer(1, 3 * mm),
        _callout("RECOMENDACIÓN FINAL", recommendation, styles, accent=BLUE, background=colors.HexColor("#EAF5FB")),
        Spacer(1, 9 * mm),
    ])

    signature_table = Table([
        ["TÉCNICO RESPONSABLE - AUTOGUARD SERVICE", "RECEPCIÓN DEL CLIENTE"],
        [_safe(vehicle.get("tecnico") or author), ""],
        ["Nombre, firma y fecha", "Nombre, firma y fecha"],
    ], colWidths=[87 * mm, 87 * mm], rowHeights=[8 * mm, 19 * mm, 7 * mm])
    signature_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([
        signature_table,
        Spacer(1, 3 * mm),
        Paragraph(
            "Documento técnico orientativo. No reemplaza inspección presencial, manual OEM, mediciones mecánicas, "
            "prueba de humo, comprobación eléctrica ni análisis de redes o funciones protegidas del fabricante.",
            styles["AGFine"],
        ),
    ])

    document.build(story, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
    return output
