from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import APP_DATA_DIR
from .dtc_database import DTCDatabase, TOTAL_DTC_RECORDS, iter_catalog

SOLUTION_DB_FILE = APP_DATA_DIR / "superscan_solutions.sqlite3"
SOLUTION_CATALOG_VERSION = "2.1.0"


@dataclass(frozen=True)
class DTCSolution:
    code: str
    severity: str
    symptoms: tuple[str, ...]
    causes: tuple[str, ...]
    tools: tuple[str, ...]
    steps: tuple[str, ...]
    validation: tuple[str, ...]
    notes: str
    source_type: str


DETAILED_SOLUTIONS: dict[str, dict[str, object]] = {
    "P0133": {
        "severity": "MEDIA",
        "symptoms": ["Respuesta lenta del sensor O2", "Consumo elevado", "Emisiones fuera de rango", "Ralentí irregular ocasional"],
        "causes": ["Sensor O2 envejecido o contaminado", "Fuga de escape antes del sensor", "Cableado o conector con alta resistencia", "Mezcla incorrecta por MAF, vacío o combustible", "Calefactor del sensor con funcionamiento deficiente"],
        "tools": ["Scanner OBD-II", "Multímetro", "Osciloscopio automotriz", "Máquina de humo", "Termómetro infrarrojo"],
        "steps": [
            "Registrar DTC, estado y Freeze Frame antes de borrar información.",
            "Comprobar si existen códigos de mezcla, MAF, encendido o calefactor O2 relacionados.",
            "Inspeccionar fugas de escape desde la culata hasta el sensor B1S1.",
            "Verificar alimentación, masa, continuidad y estado del conector del sensor.",
            "Calentar el motor a temperatura normal y observar la conmutación del sensor.",
            "Comparar la señal real con las especificaciones del fabricante; usar osciloscopio cuando sea posible.",
            "Revisar STFT y LTFT para descartar una causa de mezcla pobre o rica.",
            "Comprobar MAF, presión de combustible y fugas de vacío si los ajustes están fuera de rango.",
            "Reparar cableado, fugas o causa de mezcla antes de sustituir el sensor.",
            "Borrar DTC, realizar ciclo de conducción y confirmar que el monitor O2 complete sin recurrencia."
        ],
        "validation": ["Sin DTC confirmado o pendiente", "Señal O2 activa y estable", "STFT/LTFT dentro de rango aceptable", "Monitor O2 completado"],
    },
    "P0171": {
        "severity": "ALTA",
        "symptoms": ["Mezcla pobre banco 1", "Pérdida de potencia", "Ralentí inestable", "Tironeos", "Arranque difícil"],
        "causes": ["Fuga de vacío o admisión", "MAF contaminado o descalibrado", "Presión o caudal de combustible insuficiente", "Inyectores restringidos", "Fuga de escape previa al sensor O2", "Sensor O2 sesgado"],
        "tools": ["Scanner OBD-II", "Máquina de humo", "Manómetro de combustible", "Multímetro", "Osciloscopio", "Probador de inyectores"],
        "steps": [
            "Guardar DTC, Freeze Frame y ajustes STFT/LTFT en ralentí y a 2.500 rpm.",
            "Comprobar códigos relacionados con MAF, MAP, O2, fallas de encendido o presión de combustible.",
            "Inspeccionar ductos, PCV, servofreno, juntas y mangueras de vacío.",
            "Realizar prueba de humo en admisión y reparar cualquier fuga.",
            "Verificar lectura MAF/MAP y comparar con cilindrada, carga y especificación OEM.",
            "Medir presión residual, presión en ralentí y presión bajo carga.",
            "Comprobar balance o caudal de inyectores y calidad del combustible.",
            "Inspeccionar fugas de escape antes del sensor O2 B1S1.",
            "Reparar la causa comprobada; no sustituir sensores únicamente por el código.",
            "Borrar códigos, reiniciar adaptativos cuando el fabricante lo indique y efectuar prueba de ruta.",
            "Confirmar STFT/LTFT estables y ausencia de códigos pendientes."
        ],
        "validation": ["STFT y LTFT normalizados", "Presión de combustible conforme", "Sin fugas de admisión", "Sin DTC después de prueba de ruta"],
    },
    "P0300": {
        "severity": "CRÍTICA",
        "symptoms": ["Fallas de encendido aleatorias", "Motor tembloroso", "Pérdida de potencia", "MIL parpadeante", "Riesgo de daño al catalizador"],
        "causes": ["Bujías o bobinas defectuosas", "Inyectores o presión de combustible", "Fuga de vacío", "Compresión baja", "Sincronización mecánica", "Combustible contaminado", "Falla de sensores CKP/CMP"],
        "tools": ["Scanner con contadores de misfire", "Osciloscopio", "Probador de chispa", "Compresímetro", "Medidor leak-down", "Manómetro de combustible", "Máquina de humo"],
        "steps": [
            "No continuar conduciendo si la MIL parpadea o existe pérdida severa de potencia.",
            "Registrar Freeze Frame y contadores de falla por cilindro.",
            "Identificar si la falla se concentra en uno o varios cilindros.",
            "Inspeccionar bujías, bobinas, conectores y masas; intercambiar componentes solo como prueba controlada.",
            "Comprobar señal primaria/secundaria de encendido y alimentación de bobinas.",
            "Medir presión y volumen de combustible bajo carga.",
            "Realizar balance de inyectores y verificar pulsos de mando.",
            "Buscar fugas de admisión con humo.",
            "Medir compresión y leak-down si encendido y combustible son correctos.",
            "Verificar sincronización CKP/CMP y distribución mecánica.",
            "Reparar la causa, borrar códigos y ejecutar prueba de ruta vigilando contadores de misfire."
        ],
        "validation": ["Contadores de misfire en cero o dentro de tolerancia", "MIL apagada", "Ralentí estable", "Sin códigos pendientes", "Catalizador sin sobretemperatura"],
    },
    "P0420": {
        "severity": "ALTA",
        "symptoms": ["Eficiencia baja del catalizador banco 1", "MIL encendida", "Emisiones elevadas", "Posible pérdida de rendimiento"],
        "causes": ["Catalizador degradado", "Fallas de encendido o mezcla prolongadas", "Sensor O2 posterior lento o sesgado", "Fuga de escape", "Contaminación por aceite o refrigerante"],
        "tools": ["Scanner con gráficos O2", "Osciloscopio", "Termómetro infrarrojo", "Analizador de gases", "Máquina de humo"],
        "steps": [
            "Corregir primero cualquier código de mezcla, encendido, combustible u O2.",
            "Inspeccionar fugas de escape antes y alrededor del catalizador.",
            "Comprobar consumo de aceite o refrigerante y contaminación del escape.",
            "Comparar las señales O2 anterior y posterior a temperatura de operación.",
            "Evaluar temperatura de entrada y salida del catalizador bajo condiciones seguras.",
            "Realizar prueba de eficiencia con analizador de gases cuando esté disponible.",
            "Verificar boletines técnicos y actualización de software OEM.",
            "Sustituir el catalizador solo después de confirmar que la causa raíz fue reparada.",
            "Completar ciclo de conducción y verificar el monitor del catalizador."
        ],
        "validation": ["Monitor catalizador completado", "Señal posterior estable", "Sin DTC pendiente", "Emisiones dentro de especificación"],
    },
    "P0455": {
        "severity": "MEDIA",
        "symptoms": ["Fuga EVAP grande", "Olor a combustible", "MIL encendida", "Dificultad de carga de combustible ocasional"],
        "causes": ["Tapa de combustible ausente o defectuosa", "Manguera EVAP desconectada", "Válvula de purga abierta", "Válvula de ventilación defectuosa", "Canister o tanque con fuga"],
        "tools": ["Máquina de humo EVAP", "Scanner bidireccional", "Multímetro", "Bomba de vacío manual"],
        "steps": [
            "Inspeccionar y probar sello, cuello y tapa del depósito.",
            "Revisar visualmente mangueras EVAP, canister y conexiones.",
            "Cerrar ventilación y comandar purga según procedimiento OEM.",
            "Aplicar humo a baja presión y localizar la fuga.",
            "Probar estanqueidad y mando eléctrico de válvulas de purga y ventilación.",
            "Reparar la fuga y repetir prueba de sellado.",
            "Borrar DTC y completar monitor EVAP cuando las condiciones ambientales lo permitan."
        ],
        "validation": ["Sistema mantiene vacío/presión", "Sin fuga visible con humo", "Monitor EVAP completado", "Sin DTC pendiente"],
    },
    "U0100": {
        "severity": "CRÍTICA",
        "symptoms": ["Pérdida de comunicación con ECM/PCM", "No arranca", "Múltiples testigos", "Modo degradado", "Datos ausentes"],
        "causes": ["Batería o alimentación deficiente", "Masa de módulo defectuosa", "Circuito CAN abierto o en corto", "Conector oxidado", "Módulo fuera de línea", "Configuración o software"],
        "tools": ["Multímetro", "Osciloscopio de dos canales", "Diagrama eléctrico OEM", "Scanner de red", "Fuente estabilizada"],
        "steps": [
            "Verificar estado de batería, voltaje durante arranque y sistema de carga.",
            "Realizar escaneo completo de red e identificar todos los módulos fuera de línea.",
            "Comprobar fusibles, relés, alimentaciones y masas del ECM/PCM bajo carga.",
            "Inspeccionar conectores, humedad, corrosión y terminales desplazados.",
            "Con el sistema desenergizado, medir resistencia de terminación CAN según procedimiento OEM.",
            "Comprobar CAN High y CAN Low por cortos a masa, positivo y entre líneas.",
            "Analizar forma de onda CAN con osciloscopio.",
            "Aislar ramales o módulos únicamente siguiendo el diagrama de red.",
            "Reparar cableado o alimentación antes de condenar el módulo.",
            "Programar/configurar un módulo reemplazado y verificar comunicación total."
        ],
        "validation": ["Todos los módulos visibles", "Red CAN estable", "Sin códigos U pendientes", "Arranque y operación normales"],
    },
}


def _severity_for(code: str, system: str) -> str:
    if code.startswith(("P03", "P06", "U01", "B00")):
        return "CRÍTICA"
    if code.startswith(("P00", "P01", "P02", "P04", "P07", "C0")):
        return "ALTA"
    if system in {"Red y comunicación", "Chasis"}:
        return "ALTA"
    return "MEDIA"


def _generic_payload(code: str, system: str, scope: str) -> dict[str, object]:
    family = code[:1]
    common_tools = ["Scanner OBD-II", "Multímetro digital", "Diagrama eléctrico y especificaciones OEM"]
    if family == "P":
        symptoms = ["MIL encendida", "Rendimiento irregular según el subsistema", "Posible aumento de consumo o emisiones"]
        causes = ["Sensor o actuador relacionado", "Cableado, conector, alimentación o masa", "Condición mecánica o fluido fuera de especificación", "Calibración o software del módulo"]
        steps = [
            "Registrar el código, su estado y el Freeze Frame antes de borrar información.",
            "Leer todos los módulos y ordenar los códigos por prioridad y momento de aparición.",
            "Consultar descripción, diagrama, valores y condiciones de activación del fabricante.",
            "Realizar inspección visual del subsistema, conectores, mangueras, fluidos y daños evidentes.",
            "Verificar batería, alimentaciones y masas bajo carga.",
            "Comparar datos en vivo relacionados con valores esperados y con sensores equivalentes.",
            "Comprobar continuidad, aislamiento y caída de tensión del circuito.",
            "Ejecutar pruebas mecánicas, de presión, vacío o señal según el sistema involucrado.",
            "Reparar únicamente la causa confirmada y registrar valores antes/después.",
            "Borrar códigos, realizar ciclo de conducción y comprobar que no reaparezcan."
        ]
    elif family == "C":
        symptoms = ["Testigo ABS/ESC", "Asistencia de frenado o estabilidad limitada", "Datos de rueda o chasis incoherentes"]
        causes = ["Sensor de rueda o posición", "Anillo reluctor o componente mecánico", "Cableado/conector", "Alimentación, masa o módulo de chasis"]
        steps = [
            "Registrar DTC y datos de velocidad/posición de cada rueda.",
            "Verificar batería y alimentación de módulos ABS/ESC.",
            "Inspeccionar sensor, cableado, conectores, rodamientos y anillos reluctores.",
            "Comparar señales de sensores durante una prueba controlada.",
            "Medir continuidad, aislamiento y señal con multímetro u osciloscopio.",
            "Ejecutar calibraciones requeridas por el fabricante.",
            "Reparar, borrar DTC y confirmar operación ABS/ESC en condiciones seguras."
        ]
        common_tools += ["Osciloscopio", "Equipo de elevación seguro"]
    elif family == "B":
        symptoms = ["Testigo o función de carrocería inoperante", "Sistema de seguridad, climatización o confort limitado"]
        causes = ["Sensor/actuador de carrocería", "Conector o arnés", "Fusible/alimentación/masa", "Configuración del módulo"]
        steps = [
            "Aplicar procedimientos de seguridad, especialmente en sistemas SRS.",
            "Registrar DTC y estado de todos los módulos de carrocería.",
            "Verificar fusibles, alimentaciones, masas y conectores.",
            "Inspeccionar el componente relacionado y su instalación mecánica.",
            "Medir el circuito solo con métodos autorizados por el fabricante.",
            "Reparar o calibrar y confirmar funcionamiento completo."
        ]
    else:
        symptoms = ["Comunicación intermitente o ausente", "Múltiples testigos", "Funciones en modo degradado"]
        causes = ["Batería o masa deficiente", "Bus CAN abierto o en corto", "Conector/cableado", "Módulo sin alimentación o defectuoso"]
        steps = [
            "Comprobar batería y voltaje durante arranque.",
            "Realizar escaneo de topología y registrar módulos fuera de línea.",
            "Verificar fusibles, alimentaciones y masas bajo carga.",
            "Inspeccionar conectores, humedad y daños del arnés.",
            "Medir terminación y aislamiento de la red con el sistema desenergizado.",
            "Analizar CAN High/Low con osciloscopio y aislar el ramal defectuoso.",
            "Reparar la causa, configurar módulos cuando corresponda y repetir escaneo."
        ]
        common_tools += ["Osciloscopio de dos canales", "Scanner de red"]

    note = (
        f"Procedimiento offline de orientación para código {scope.lower()}. "
        "Los valores, pines, pares de apriete, presiones y secuencias deben confirmarse en información OEM del vehículo."
    )
    return {
        "severity": _severity_for(code, system),
        "symptoms": symptoms,
        "causes": causes,
        "tools": common_tools,
        "steps": steps,
        "validation": ["Causa raíz documentada", "Reparación verificada", "Sin DTC confirmado ni pendiente", "Prueba funcional o de ruta completada"],
        "notes": note,
        "source_type": "Procedimiento propio offline",
    }


def _iter_solution_rows() -> Iterable[tuple[str, str, str, str, str, str, str, str, str]]:
    for code, _description, system, scope in iter_catalog():
        payload = _generic_payload(code, system, scope)
        override = DETAILED_SOLUTIONS.get(code)
        if override:
            payload.update(override)
            payload["notes"] = "Procedimiento técnico propio. Confirmar valores y condiciones exactas con documentación OEM."
            payload["source_type"] = "Procedimiento detallado offline"
        yield (
            code,
            str(payload["severity"]),
            json.dumps(payload["symptoms"], ensure_ascii=False),
            json.dumps(payload["causes"], ensure_ascii=False),
            json.dumps(payload["tools"], ensure_ascii=False),
            json.dumps(payload["steps"], ensure_ascii=False),
            json.dumps(payload["validation"], ensure_ascii=False),
            str(payload["notes"]),
            str(payload["source_type"]),
        )


class SolutionDatabase:
    def __init__(self, dtc_db: DTCDatabase, path: Path = SOLUTION_DB_FILE):
        self.dtc_db = dtc_db
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS solutions (
                    code TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    symptoms_json TEXT NOT NULL,
                    causes_json TEXT NOT NULL,
                    tools_json TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    validation_json TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    source_type TEXT NOT NULL
                )
                """
            )
            version = conn.execute("SELECT value FROM metadata WHERE key='catalog_version'").fetchone()
            count = int(conn.execute("SELECT COUNT(*) FROM solutions").fetchone()[0])
            if version is None or version["value"] != SOLUTION_CATALOG_VERSION or count != TOTAL_DTC_RECORDS:
                conn.execute("DELETE FROM solutions")
                conn.executemany(
                    """
                    INSERT INTO solutions(
                        code, severity, symptoms_json, causes_json, tools_json,
                        steps_json, validation_json, notes, source_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _iter_solution_rows(),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('catalog_version', ?)",
                    (SOLUTION_CATALOG_VERSION,),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('record_count', ?)",
                    (str(TOTAL_DTC_RECORDS),),
                )
                conn.commit()

    @staticmethod
    def _row_to_solution(row: sqlite3.Row) -> DTCSolution:
        return DTCSolution(
            code=row["code"],
            severity=row["severity"],
            symptoms=tuple(json.loads(row["symptoms_json"])),
            causes=tuple(json.loads(row["causes_json"])),
            tools=tuple(json.loads(row["tools_json"])),
            steps=tuple(json.loads(row["steps_json"])),
            validation=tuple(json.loads(row["validation_json"])),
            notes=row["notes"],
            source_type=row["source_type"],
        )

    def lookup(self, code: str) -> DTCSolution:
        normalized = code.strip().upper()
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM solutions WHERE code=?", (normalized,)).fetchone()
        if row:
            return self._row_to_solution(row)
        record = self.dtc_db.lookup(normalized)
        payload = _generic_payload(normalized, record.system, record.scope)
        return DTCSolution(
            code=normalized,
            severity=str(payload["severity"]),
            symptoms=tuple(payload["symptoms"]),
            causes=tuple(payload["causes"]),
            tools=tuple(payload["tools"]),
            steps=tuple(payload["steps"]),
            validation=tuple(payload["validation"]),
            notes=str(payload["notes"]),
            source_type=str(payload["source_type"]),
        )

    def count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM solutions").fetchone()[0])
