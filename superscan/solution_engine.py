from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import DB_FILE
from .dtc_database import TOTAL_DTC_RECORDS, iter_catalog


SOLUTION_DB_VERSION = "2.1.0"


@dataclass(frozen=True)
class DiagnosticGuide:
    code: str
    severity: str
    summary: str
    symptoms: tuple[str, ...]
    causes: tuple[str, ...]
    steps: tuple[str, ...]
    tools: tuple[str, ...]
    validation: tuple[str, ...]
    safety_notice: str
    source_scope: str = "Procedimiento orientativo offline AutoGuard"


CURATED_GUIDES: dict[str, DiagnosticGuide] = {
    "P0133": DiagnosticGuide(
        code="P0133",
        severity="MEDIA",
        summary="Respuesta lenta del sensor de oxígeno B1S1. La ECU detectó que la señal cambia con una velocidad inferior a la esperada.",
        symptoms=("Aumento de consumo", "Ralentí irregular", "Emisiones elevadas", "Luz MIL encendida"),
        causes=("Sensor de oxígeno envejecido", "Fuga de escape antes del sensor", "Mezcla incorrecta", "Cableado o calefactor defectuoso"),
        steps=(
            "Registrar DTC y Freeze Frame antes de borrar códigos.",
            "Revisar visualmente arnés, conectores y aislamiento del sensor B1S1.",
            "Inspeccionar fugas de escape antes del sensor.",
            "Comprobar alimentación, masa y resistencia del calefactor según especificación.",
            "Graficar la señal O2 con el motor a temperatura de operación.",
            "Verificar STFT y LTFT para descartar mezcla pobre o rica.",
            "Reparar la causa encontrada o reemplazar el sensor solo después de confirmar la falla.",
            "Borrar DTC, realizar ciclo de conducción y confirmar que el monitor complete sin reaparecer.",
        ),
        tools=("Escáner OBD-II", "Multímetro", "Osciloscopio recomendado", "Equipo de humo si se sospecha fuga"),
        validation=("Señal O2 conmuta con rapidez normal", "Ajustes de combustible dentro de rango", "Monitor O2 completado", "DTC no reaparece"),
        safety_notice="Trabajar con el escape frío cuando se inspeccionen conectores o fugas.",
    ),
    "P0171": DiagnosticGuide(
        code="P0171",
        severity="ALTA",
        summary="Mezcla demasiado pobre en banco 1. La ECU está agregando combustible para compensar exceso de aire o falta de combustible.",
        symptoms=("Pérdida de potencia", "Ralentí inestable", "Tironeos", "Consumo anormal", "MIL encendida"),
        causes=("Fuga de vacío", "MAF contaminado o defectuoso", "Baja presión de combustible", "Inyectores restringidos", "Fuga de escape"),
        steps=(
            "Registrar todos los DTC y revisar Freeze Frame.",
            "Observar STFT y LTFT en ralentí y a 2.500 rpm.",
            "Inspeccionar mangueras, PCV, múltiple y ductos después del MAF.",
            "Realizar prueba de humo en admisión si no se observa fuga.",
            "Verificar MAF, MAP y temperatura de admisión comparando valores plausibles.",
            "Medir presión y caudal de combustible bajo carga.",
            "Ejecutar balance de inyectores cuando el equipo lo permita.",
            "Reparar la causa confirmada; no reemplazar piezas por descarte.",
            "Borrar adaptativos solo cuando corresponda y realizar prueba de ruta.",
            "Confirmar STFT/LTFT estables y ausencia del DTC.",
        ),
        tools=("Escáner con gráficos", "Equipo de humo", "Manómetro de combustible", "Multímetro", "Limpiador MAF aprobado"),
        validation=("STFT y LTFT dentro de ±10 %", "Presión de combustible conforme", "Sin fugas", "DTC no reaparece"),
        safety_notice="Despresurizar el sistema antes de intervenir la línea de combustible.",
    ),
    "P0300": DiagnosticGuide(
        code="P0300",
        severity="ALTA",
        summary="Falla de encendido aleatoria o múltiple. Puede dañar el catalizador si el vehículo continúa operando con la MIL parpadeando.",
        symptoms=("Motor vibra", "Pérdida de potencia", "MIL parpadea", "Olor a combustible", "Dificultad de arranque"),
        causes=("Encendido defectuoso", "Inyector o presión de combustible", "Compresión baja", "Entrada de aire falsa", "Sincronización incorrecta"),
        steps=(
            "Detener el uso exigente si la MIL parpadea.",
            "Registrar contadores de misfire y Freeze Frame.",
            "Identificar cilindros afectados y condición de carga.",
            "Revisar bujías, bobinas, cables y aislamiento.",
            "Intercambiar componentes solo como prueba controlada y registrar el resultado.",
            "Verificar presión de combustible e inyectores.",
            "Medir compresión y fuga de cilindros si el encendido es correcto.",
            "Comprobar sincronización mecánica y señales CKP/CMP.",
            "Reparar la causa y confirmar con prueba de ruta bajo condiciones similares.",
        ),
        tools=("Escáner con Mode 06", "Probador de chispa", "Multímetro", "Compresímetro", "Probador de fugas"),
        validation=("Contadores de misfire en cero o normales", "Ralentí estable", "Catalizador sin sobretemperatura", "DTC no reaparece"),
        safety_notice="Una MIL parpadeante indica riesgo de daño térmico al catalizador.",
    ),
    "P0420": DiagnosticGuide(
        code="P0420",
        severity="MEDIA",
        summary="Eficiencia del catalizador por debajo del umbral en banco 1. Deben descartarse fallas de mezcla, encendido y fugas antes de condenar el catalizador.",
        symptoms=("MIL encendida", "Emisiones elevadas", "Posible pérdida de rendimiento", "Generalmente sin síntomas severos"),
        causes=("Catalizador degradado", "Falla de encendido previa", "Mezcla incorrecta", "Fuga de escape", "Sensor O2 lento"),
        steps=(
            "Registrar DTC relacionados y Freeze Frame.",
            "Reparar primero misfire, mezcla o consumo de aceite.",
            "Inspeccionar fugas de escape antes y alrededor del catalizador.",
            "Comparar gráficamente sensores O2 anterior y posterior.",
            "Verificar temperatura de entrada y salida bajo condiciones controladas.",
            "Confirmar que el motor alcance temperatura normal.",
            "Evaluar el catalizador solo cuando los demás sistemas estén conformes.",
            "Borrar códigos y completar el monitor de catalizador.",
        ),
        tools=("Escáner con gráficos", "Termómetro infrarrojo", "Equipo de humo", "Analizador de gases recomendado"),
        validation=("Monitor de catalizador completado", "Sensores O2 con comportamiento esperado", "Sin DTC de mezcla o misfire", "P0420 no reaparece"),
        safety_notice="El catalizador alcanza temperaturas extremadamente altas.",
    ),
    "P0455": DiagnosticGuide(
        code="P0455",
        severity="MEDIA",
        summary="Fuga grande detectada en el sistema EVAP. Puede deberse a tapa, manguera abierta, válvula o fuga de gran tamaño.",
        symptoms=("MIL encendida", "Olor a combustible", "Dificultad ocasional de carga", "Sin cambio de conducción en muchos casos"),
        causes=("Tapa de combustible suelta", "Manguera desconectada", "Válvula de purga abierta", "Válvula de ventilación defectuosa", "Canister dañado"),
        steps=(
            "Revisar tapa de combustible, sello y cuello de carga.",
            "Inspeccionar mangueras EVAP desde el tanque hasta el motor.",
            "Comandar válvulas de purga y ventilación cuando el equipo lo permita.",
            "Verificar que la válvula de purga no quede abierta sin comando.",
            "Realizar prueba de humo con presión regulada para EVAP.",
            "Reparar la fuga identificada.",
            "Borrar DTC y completar el monitor EVAP según condiciones de conducción.",
        ),
        tools=("Escáner bidireccional recomendado", "Equipo de humo EVAP", "Multímetro", "Bomba de vacío manual"),
        validation=("Sistema mantiene vacío/presión", "Válvulas responden", "Sin olor a combustible", "Monitor EVAP completado"),
        safety_notice="No usar fuentes de ignición cerca de vapores de combustible.",
    ),
    "U0100": DiagnosticGuide(
        code="U0100",
        severity="CRÍTICA",
        summary="Comunicación perdida con ECM/PCM. Puede impedir el arranque o afectar múltiples sistemas.",
        symptoms=("No arranca", "Múltiples testigos", "Datos ECU ausentes", "Modo de emergencia"),
        causes=("Batería o alimentación deficiente", "Masa defectuosa", "Bus CAN abierto o en corto", "Conector corroído", "Módulo fuera de línea"),
        steps=(
            "Comprobar batería bajo carga y tensión durante arranque.",
            "Realizar escaneo completo de todos los módulos disponibles.",
            "Verificar fusibles, relés, alimentaciones y masas del ECM/PCM.",
            "Medir resistencia del bus CAN con el sistema desenergizado según procedimiento.",
            "Comprobar CAN-H y CAN-L con osciloscopio.",
            "Aislar ramales o módulos solo siguiendo el diagrama del fabricante.",
            "Reparar cableado, terminales o alimentación antes de reemplazar módulos.",
            "Programar/configurar el módulo únicamente cuando esté confirmado.",
        ),
        tools=("Escáner multimódulo", "Multímetro", "Osciloscopio", "Diagramas eléctricos OEM"),
        validation=("ECM/PCM comunica establemente", "Resistencia y señales CAN correctas", "Vehículo arranca", "No reaparecen códigos U"),
        safety_notice="Desconectar la batería según el procedimiento del fabricante antes de intervenir conectores de módulos.",
    ),
}


def _severity(code: str) -> str:
    critical = {"P0217", "P0606", "P0611", "U0100", "U0101", "U0121", "B0001", "B0012"}
    high_prefixes = ("P03", "P02", "P07", "C00", "C01")
    if code in critical:
        return "CRÍTICA"
    if code.startswith(high_prefixes):
        return "ALTA"
    if code.startswith(("P04", "P01", "U", "B")):
        return "MEDIA"
    return "BAJA"


def _family_templates(code: str, description: str, system: str) -> DiagnosticGuide:
    family = code[:1] or "P"
    severity = _severity(code)
    common_open = (
        "Registrar el código, estado y Freeze Frame antes de borrar.",
        "Comprobar si existen códigos relacionados que puedan ser la causa primaria.",
        "Realizar inspección visual de conectores, arnés, terminales, fusibles y masas.",
    )
    common_close = (
        "Reparar únicamente la causa confirmada mediante medición.",
        "Borrar códigos después de la reparación.",
        "Realizar prueba funcional y ciclo de conducción.",
        "Reescanear y confirmar que el código no reaparece.",
    )
    if family == "P":
        causes = (
            "Sensor o actuador fuera de rango",
            "Circuito abierto, cortocircuito o resistencia alta",
            "Alimentación o masa deficiente",
            "Condición mecánica, combustible o admisión relacionada",
            "Calibración o módulo de control",
        )
        middle = (
            "Comparar datos en vivo con valores plausibles y con sensores relacionados.",
            "Verificar alimentación de referencia, masa y señal usando diagrama eléctrico.",
            "Ejecutar pruebas mecánicas o de presión según el sistema afectado.",
            "Consultar boletines y especificaciones del fabricante para el vehículo exacto.",
        )
        symptoms = ("MIL encendida", "Rendimiento reducido posible", "Consumo o emisiones alterados", "Síntomas variables según el circuito")
        tools = ("Escáner OBD-II", "Multímetro", "Diagrama eléctrico", "Herramienta específica del sistema")
        safety = "Aplicar procedimientos de seguridad para combustible, temperatura, piezas móviles y alta tensión cuando corresponda."
    elif family == "C":
        causes = ("Sensor de rueda o posición", "Arnés cerca de suspensión", "Rodamiento o anillo reluctor", "Alimentación del módulo", "Calibración requerida")
        middle = (
            "Comparar velocidades o señales de sensores durante una prueba controlada.",
            "Inspeccionar cableado sometido a movimiento, humedad o impacto.",
            "Medir señal y continuidad conforme al tipo de sensor.",
            "Verificar rodamiento, reluctor, holgura y montaje.",
        )
        symptoms = ("Testigo ABS/ESC", "Asistencia de estabilidad deshabilitada", "Frenado base generalmente disponible", "Señal intermitente")
        tools = ("Escáner ABS", "Multímetro", "Osciloscopio recomendado", "Elevador y herramientas de inspección")
        safety = "Asegurar el vehículo antes de elevarlo y no realizar pruebas de rueda sin medidas de contención."
    elif family == "B":
        causes = ("Conector o terminal", "Alimentación/masa", "Sensor o actuador de carrocería", "Configuración", "Módulo de control")
        middle = (
            "Identificar el módulo que originó el DTC y verificar comunicación.",
            "Revisar alimentaciones, masas y conectores del circuito.",
            "Ejecutar prueba activa cuando sea segura y esté disponible.",
            "Verificar calibración o aprendizaje requerido.",
        )
        symptoms = ("Función de carrocería inoperativa", "Testigo de seguridad posible", "Operación intermitente", "Mensaje en tablero")
        tools = ("Escáner multimódulo", "Multímetro", "Diagrama eléctrico", "Herramienta de programación si corresponde")
        safety = "En sistemas SRS, esperar el tiempo especificado después de desconectar la batería y no medir iniciadores con instrumentos no autorizados."
    else:
        causes = ("Tensión de batería baja", "Terminación CAN incorrecta", "Circuito CAN abierto o en corto", "Módulo sin alimentación", "Módulo o gateway fuera de línea")
        middle = (
            "Realizar escaneo completo y registrar módulos ausentes.",
            "Comprobar batería, fusibles, alimentaciones y masas.",
            "Medir resistencia y forma de onda de la red siguiendo el diagrama.",
            "Aislar ramales o módulos de manera controlada.",
        )
        symptoms = ("Múltiples testigos", "Funciones intermitentes", "Módulo no comunica", "Posible no-arranque")
        tools = ("Escáner multimódulo", "Multímetro", "Osciloscopio", "Topología de red OEM")
        safety = "Desenergizar módulos y redes según el procedimiento del fabricante antes de desconectar componentes."
    return DiagnosticGuide(
        code=code,
        severity=severity,
        summary=f"{description} Procedimiento offline orientativo para el sistema {system}.",
        symptoms=tuple(symptoms),
        causes=tuple(causes),
        steps=tuple(common_open + middle + common_close),
        tools=tuple(tools),
        validation=("Valores y señales dentro de especificación", "Función restaurada", "Monitores completados cuando corresponda", "DTC ausente después de la prueba"),
        safety_notice=safety,
    )


def build_guide(code: str, description: str, system: str) -> DiagnosticGuide:
    normalized = code.strip().upper()
    return CURATED_GUIDES.get(normalized) or _family_templates(normalized, description, system)


class OfflineSolutionDatabase:
    def __init__(self, path: Path = DB_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dtc_solution (
                    code TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE TABLE IF NOT EXISTS solution_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            version = conn.execute("SELECT value FROM solution_metadata WHERE key='version'").fetchone()
            count = conn.execute("SELECT COUNT(*) FROM dtc_solution").fetchone()[0]
            if version is None or version["value"] != SOLUTION_DB_VERSION or count != TOTAL_DTC_RECORDS:
                conn.execute("DELETE FROM dtc_solution")
                rows = []
                for code, description, system, _scope in iter_catalog():
                    guide = build_guide(code, description, system)
                    rows.append((code, guide.severity, json.dumps(asdict(guide), ensure_ascii=False)))
                    if len(rows) >= 500:
                        conn.executemany("INSERT INTO dtc_solution(code, severity, payload) VALUES (?, ?, ?)", rows)
                        rows.clear()
                if rows:
                    conn.executemany("INSERT INTO dtc_solution(code, severity, payload) VALUES (?, ?, ?)", rows)
                conn.execute("INSERT OR REPLACE INTO solution_metadata(key, value) VALUES ('version', ?)", (SOLUTION_DB_VERSION,))
                conn.execute("INSERT OR REPLACE INTO solution_metadata(key, value) VALUES ('count', ?)", (str(TOTAL_DTC_RECORDS),))
                conn.commit()

    def lookup(self, code: str, description: str = "Código DTC", system: str = "Sistema relacionado") -> DiagnosticGuide:
        normalized = code.strip().upper()
        with self.connect() as conn:
            row = conn.execute("SELECT payload FROM dtc_solution WHERE code=?", (normalized,)).fetchone()
        if row:
            data = json.loads(row["payload"])
            for key in ("symptoms", "causes", "steps", "tools", "validation"):
                data[key] = tuple(data[key])
            return DiagnosticGuide(**data)
        return build_guide(normalized, description, system)

    def count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM dtc_solution").fetchone()[0])
