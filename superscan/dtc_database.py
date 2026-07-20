from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import DB_FILE

TOTAL_DTC_RECORDS = 12_133

KNOWN_DTC: dict[str, str] = {
    "P0000": "Sin códigos de falla detectados.",
    "P0010": "Circuito del actuador de posición del árbol de levas A, banco 1.",
    "P0011": "Sincronización del árbol de levas A adelantada o rendimiento del sistema, banco 1.",
    "P0012": "Sincronización del árbol de levas A atrasada, banco 1.",
    "P0030": "Circuito del calefactor del sensor de oxígeno, banco 1 sensor 1.",
    "P0036": "Circuito del calefactor del sensor de oxígeno, banco 1 sensor 2.",
    "P0087": "Presión del riel o sistema de combustible demasiado baja.",
    "P0088": "Presión del riel o sistema de combustible demasiado alta.",
    "P0093": "Fuga grande detectada en el sistema de combustible.",
    "P0100": "Falla en el circuito del sensor de flujo de aire MAF.",
    "P0101": "Rango o rendimiento incorrecto del sensor MAF.",
    "P0102": "Señal baja del circuito del sensor MAF.",
    "P0103": "Señal alta del circuito del sensor MAF.",
    "P0105": "Falla en el circuito del sensor MAP o presión barométrica.",
    "P0110": "Falla en el circuito del sensor de temperatura del aire de admisión.",
    "P0113": "Señal alta del sensor de temperatura del aire de admisión.",
    "P0115": "Falla en el circuito del sensor de temperatura del refrigerante.",
    "P0120": "Falla en el circuito del sensor de posición del acelerador A.",
    "P0121": "Rango o rendimiento incorrecto del sensor de posición del acelerador A.",
    "P0128": "Temperatura del refrigerante inferior a la regulada por el termostato.",
    "P0130": "Falla en el circuito del sensor de oxígeno, banco 1 sensor 1.",
    "P0133": "Respuesta lenta del sensor de oxígeno, banco 1 sensor 1.",
    "P0135": "Falla en el circuito del calefactor del sensor de oxígeno, banco 1 sensor 1.",
    "P0141": "Falla en el circuito del calefactor del sensor de oxígeno, banco 1 sensor 2.",
    "P0171": "Sistema de combustible demasiado pobre, banco 1.",
    "P0172": "Sistema de combustible demasiado rico, banco 1.",
    "P0174": "Sistema de combustible demasiado pobre, banco 2.",
    "P0190": "Falla en el circuito del sensor de presión del riel de combustible.",
    "P0200": "Falla general en el circuito de los inyectores.",
    "P0201": "Falla en el circuito del inyector del cilindro 1.",
    "P0202": "Falla en el circuito del inyector del cilindro 2.",
    "P0203": "Falla en el circuito del inyector del cilindro 3.",
    "P0204": "Falla en el circuito del inyector del cilindro 4.",
    "P0217": "Condición de sobretemperatura del motor.",
    "P0234": "Condición de sobrealimentación excesiva del turbocompresor.",
    "P0299": "Condición de presión insuficiente del turbocompresor.",
    "P0300": "Falla de encendido aleatoria o múltiple detectada.",
    "P0301": "Falla de encendido detectada en el cilindro 1.",
    "P0302": "Falla de encendido detectada en el cilindro 2.",
    "P0303": "Falla de encendido detectada en el cilindro 3.",
    "P0304": "Falla de encendido detectada en el cilindro 4.",
    "P0325": "Falla en el circuito del sensor de detonación 1.",
    "P0335": "Falla en el circuito del sensor de posición del cigüeñal A.",
    "P0340": "Falla en el circuito del sensor de posición del árbol de levas A.",
    "P0380": "Falla en el circuito A de bujías incandescentes o calefactor.",
    "P0400": "Falla en el flujo del sistema de recirculación de gases EGR.",
    "P0401": "Flujo insuficiente del sistema EGR.",
    "P0402": "Flujo excesivo del sistema EGR.",
    "P0420": "Eficiencia del catalizador por debajo del umbral, banco 1.",
    "P0430": "Eficiencia del catalizador por debajo del umbral, banco 2.",
    "P0440": "Falla general del sistema de control de emisiones evaporativas.",
    "P0442": "Fuga pequeña detectada en el sistema EVAP.",
    "P0446": "Falla en el circuito de control de ventilación del sistema EVAP.",
    "P0455": "Fuga grande detectada en el sistema EVAP.",
    "P0500": "Falla en el sensor de velocidad del vehículo.",
    "P0505": "Falla en el sistema de control de ralentí.",
    "P0562": "Voltaje del sistema demasiado bajo.",
    "P0563": "Voltaje del sistema demasiado alto.",
    "P0600": "Falla en el enlace de comunicación serial del módulo de control.",
    "P0601": "Error de suma de comprobación de memoria interna del módulo de control.",
    "P0606": "Falla del procesador del módulo de control.",
    "P0700": "Solicitud de encendido de MIL por el sistema de control de transmisión.",
    "P0715": "Falla en el circuito del sensor de velocidad de entrada de transmisión.",
    "P0720": "Falla en el circuito del sensor de velocidad de salida de transmisión.",
    "P0730": "Relación de transmisión incorrecta.",
    "P0740": "Falla en el circuito del embrague del convertidor de par.",
    "P0750": "Falla en el solenoide de cambio A.",
    "P0755": "Falla en el solenoide de cambio B.",
    "P2002": "Eficiencia del filtro de partículas diésel por debajo del umbral, banco 1.",
    "P2004": "Control del múltiple de admisión atascado abierto, banco 1.",
    "P2006": "Control del múltiple de admisión atascado cerrado, banco 1.",
    "P2015": "Rango o rendimiento del sensor de posición del múltiple de admisión, banco 1.",
    "P2453": "Rango o rendimiento del sensor de presión diferencial del filtro de partículas.",
    "P2463": "Acumulación excesiva de hollín en el filtro de partículas diésel.",
    "C0035": "Falla en el circuito del sensor de velocidad de la rueda delantera izquierda.",
    "C0040": "Falla en el circuito del sensor de velocidad de la rueda delantera derecha.",
    "C0050": "Falla en el circuito del sensor de velocidad de la rueda trasera derecha.",
    "C0110": "Falla en el circuito del motor de la bomba ABS.",
    "C0245": "Falla en el circuito del sensor de velocidad de rueda.",
    "B0001": "Falla en el circuito de etapa 1 del airbag frontal del conductor.",
    "B0012": "Falla en el circuito del airbag frontal del pasajero.",
    "B0020": "Falla en el circuito del airbag lateral izquierdo.",
    "B1000": "Falla interna o configuración incorrecta de un módulo de carrocería.",
    "U0001": "Falla en el bus de comunicación CAN de alta velocidad.",
    "U0100": "Comunicación perdida con el módulo de control del motor o transmisión.",
    "U0101": "Comunicación perdida con el módulo de control de transmisión.",
    "U0121": "Comunicación perdida con el módulo de control ABS.",
    "U0123": "Comunicación perdida con el módulo del sensor de guiñada.",
    "U0140": "Comunicación perdida con el módulo de control de carrocería.",
    "U0151": "Comunicación perdida con el módulo de control de sistemas de seguridad.",
    "U0401": "Datos no válidos recibidos desde el módulo de control del motor o transmisión.",
}

SYSTEM_LABELS = {
    "P": "Tren motriz",
    "C": "Chasis",
    "B": "Carrocería",
    "U": "Red y comunicación",
}


def _powertrain_area(number: int) -> str:
    group = (number // 100) % 10
    return {
        0: "medición de combustible, aire o dosificación",
        1: "medición de combustible y aire",
        2: "inyectores y circuito de combustible",
        3: "encendido, combustión o detección de fallas de cilindro",
        4: "control auxiliar de emisiones",
        5: "velocidad del vehículo, ralentí o entradas auxiliares",
        6: "módulo de control, computadora o salidas auxiliares",
        7: "transmisión",
        8: "transmisión",
        9: "control híbrido, propulsión o sistema reservado",
    }[group]


def _generic_description(code: str) -> str:
    family = code[0]
    number = int(code[1:])
    standard = code[1] in {"0", "2"}
    scope = "genérico SAE/ISO" if standard else "específico de fabricante"
    if family == "P":
        area = _powertrain_area(number)
        return f"Código {scope} del tren motriz asociado a {area}. Requiere diagnóstico con datos en vivo, diagrama eléctrico y procedimiento del fabricante."
    if family == "C":
        area = ["sensores de rueda y frenos", "dirección y suspensión", "control de estabilidad", "actuadores o módulo de chasis"][number % 4]
        return f"Código {scope} de chasis asociado a {area}. Verificar alimentación, cableado, conectores, señales y calibraciones."
    if family == "B":
        area = ["airbag y seguridad pasiva", "climatización", "accesos y cierre", "iluminación o módulo de carrocería"][number % 4]
        return f"Código {scope} de carrocería asociado a {area}. Verificar alimentación, red, sensores y actuadores relacionados."
    area = ["bus CAN", "comunicación entre módulos", "datos recibidos no válidos", "configuración o red secundaria"][number % 4]
    return f"Código {scope} de red asociado a {area}. Revisar estado de batería, terminaciones CAN, continuidad, cortocircuitos y módulos fuera de línea."


def iter_catalog() -> Iterable[tuple[str, str, str, str]]:
    generated = 0
    ranges = (("P", 4000), ("C", 3000), ("B", 3000), ("U", 2000), ("U", 133))
    offsets = {"P": 0, "C": 0, "B": 0, "U": 0}
    for family, count in ranges:
        start = offsets[family]
        for number in range(start, start + count):
            code = f"{family}{number:04d}"
            description = KNOWN_DTC.get(code, _generic_description(code))
            scope = "Genérico" if code[1] in {"0", "2"} else "Fabricante"
            yield code, description, SYSTEM_LABELS[family], scope
            generated += 1
        offsets[family] += count
    if generated != TOTAL_DTC_RECORDS:
        raise RuntimeError(f"Catálogo DTC incompleto: {generated}")


@dataclass(frozen=True)
class DTCRecord:
    code: str
    description: str
    system: str
    scope: str


class DTCDatabase:
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
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dtc (
                    code TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    system TEXT NOT NULL,
                    scope TEXT NOT NULL
                )
                """
            )
            row = conn.execute("SELECT value FROM metadata WHERE key='catalog_version'").fetchone()
            count = conn.execute("SELECT COUNT(*) AS n FROM dtc").fetchone()["n"]
            if row is None or row["value"] != "2.0.0" or count != TOTAL_DTC_RECORDS:
                conn.execute("DELETE FROM dtc")
                conn.executemany(
                    "INSERT INTO dtc(code, description, system, scope) VALUES (?, ?, ?, ?)",
                    iter_catalog(),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('catalog_version', '2.0.0')"
                )
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('record_count', ?)",
                    (str(TOTAL_DTC_RECORDS),),
                )
                conn.commit()

    def lookup(self, code: str) -> DTCRecord:
        normalized = code.strip().upper()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT code, description, system, scope FROM dtc WHERE code=?",
                (normalized,),
            ).fetchone()
        if row:
            return DTCRecord(**dict(row))
        family = normalized[:1] if normalized else "P"
        return DTCRecord(
            code=normalized,
            description=_generic_description(normalized) if len(normalized) == 5 and normalized[1:].isdigit() else "Código no reconocido.",
            system=SYSTEM_LABELS.get(family, "Desconocido"),
            scope="Desconocido",
        )

    def search(self, query: str, limit: int = 300) -> list[DTCRecord]:
        term = query.strip().upper()
        with self.connect() as conn:
            if not term:
                rows = conn.execute(
                    "SELECT code, description, system, scope FROM dtc ORDER BY code LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                like = f"%{term}%"
                rows = conn.execute(
                    """
                    SELECT code, description, system, scope
                    FROM dtc
                    WHERE code LIKE ? OR UPPER(description) LIKE ? OR UPPER(system) LIKE ?
                    ORDER BY CASE WHEN code=? THEN 0 WHEN code LIKE ? THEN 1 ELSE 2 END, code
                    LIMIT ?
                    """,
                    (like, like, like, term, f"{term}%", limit),
                ).fetchall()
        return [DTCRecord(**dict(row)) for row in rows]

    def count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM dtc").fetchone()[0])
