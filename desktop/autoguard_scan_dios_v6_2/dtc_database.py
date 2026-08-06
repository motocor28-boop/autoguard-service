from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DTCRecord:
    code: str
    description: str
    manufacturer: str
    is_generic: bool
    source: str


@dataclass(slots=True)
class DTCSolution:
    code: str
    manufacturer: str
    system: str
    severity: str
    symptoms: str
    causes: str
    steps: str
    validation: str
    sensors: str
    tools: str
    source: str


SPANISH_OVERRIDES = {
    "U0123": "Pérdida de comunicación con el módulo del sensor de velocidad de guiñada",
    "P0100": "Falla en el circuito del sensor de flujo de aire MAF",
    "P0101": "Rango o rendimiento incorrecto del sensor MAF",
    "P0113": "Entrada alta del sensor de temperatura de aire de admisión",
    "P0128": "Temperatura del refrigerante inferior a la regulada por el termostato",
    "P0133": "Respuesta lenta del sensor de oxígeno, banco 1 sensor 1",
    "P0171": "Sistema demasiado pobre, banco 1",
    "P0172": "Sistema demasiado rico, banco 1",
    "P0300": "Falla de encendido aleatoria o múltiple detectada",
    "P0301": "Falla de encendido detectada en el cilindro 1",
    "P0302": "Falla de encendido detectada en el cilindro 2",
    "P0303": "Falla de encendido detectada en el cilindro 3",
    "P0304": "Falla de encendido detectada en el cilindro 4",
    "P0401": "Flujo insuficiente del sistema EGR",
    "P0420": "Eficiencia del catalizador por debajo del umbral, banco 1",
    "P0442": "Fuga pequeña detectada en el sistema EVAP",
    "P0455": "Fuga grande detectada en el sistema EVAP",
    "P0500": "Falla del sensor de velocidad del vehículo",
    "P0562": "Voltaje bajo del sistema",
    "P0700": "Solicitud de encendido MIL del sistema de transmisión",
    "U0100": "Pérdida de comunicación con el módulo de control del motor o transmisión",
    "U0121": "Pérdida de comunicación con el módulo de control ABS",
}


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


class DtcDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or resource_path("data/autoguard_dtc.sqlite")
        if not self.path.is_file():
            raise FileNotFoundError(f"Base DTC no encontrada: {self.path}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _record(row: sqlite3.Row) -> DTCRecord:
        code = row["code"].upper()
        description = SPANISH_OVERRIDES.get(code, row["description"])
        return DTCRecord(
            code=code,
            description=description,
            manufacturer=row["manufacturer"],
            is_generic=bool(row["is_generic"]),
            source=row["source"],
        )

    @staticmethod
    def _solution(row: sqlite3.Row) -> DTCSolution:
        return DTCSolution(
            code=row["code"], manufacturer=row["manufacturer"], system=row["system"],
            severity=row["severity"], symptoms=row["symptoms"], causes=row["causes"],
            steps=row["steps"], validation=row["validation"], sensors=row["sensors"],
            tools=row["tools"], source=row["source"],
        )

    def lookup(self, code: str, manufacturer: str | None = None) -> list[DTCRecord]:
        code = code.strip().upper().replace(" ", "")
        if not code:
            return []
        with self._connect() as connection:
            if manufacturer and manufacturer.lower() not in {"", "genérico", "generico", "todos"}:
                rows = connection.execute(
                    """SELECT code, description, manufacturer, is_generic, source
                    FROM dtc WHERE code = ? AND (manufacturer = ? OR is_generic = 1)
                    ORDER BY is_generic DESC, manufacturer""",
                    (code, manufacturer),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT code, description, manufacturer, is_generic, source
                    FROM dtc WHERE code = ? ORDER BY is_generic DESC, manufacturer""",
                    (code,),
                ).fetchall()
        return [self._record(row) for row in rows]

    def search(self, text: str, manufacturer: str | None = None, limit: int = 250) -> list[DTCRecord]:
        text = text.strip()
        like = f"%{text}%"
        params: list[object] = [like, like]
        condition = "(code LIKE ? OR description LIKE ?)"
        if manufacturer and manufacturer.lower() not in {"", "todos"}:
            condition += " AND (manufacturer = ? OR is_generic = 1)"
            params.append(manufacturer)
        params.append(max(1, min(limit, 1000)))
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT code, description, manufacturer, is_generic, source
                FROM dtc WHERE {condition}
                ORDER BY code, is_generic DESC, manufacturer LIMIT ?""",
                params,
            ).fetchall()
        return [self._record(row) for row in rows]

    def solution(self, code: str, manufacturer: str | None = None) -> DTCSolution | None:
        code = code.strip().upper().replace(" ", "")
        if not code:
            return None
        with self._connect() as connection:
            if manufacturer and manufacturer.lower() not in {"", "todos", "sae/iso", "genérico", "generico"}:
                row = connection.execute(
                    """SELECT * FROM solutions WHERE code = ? AND manufacturer = ? LIMIT 1""",
                    (code, manufacturer),
                ).fetchone()
                if row is None:
                    row = connection.execute(
                        """SELECT * FROM solutions WHERE code = ? AND manufacturer = 'SAE/ISO' LIMIT 1""",
                        (code,),
                    ).fetchone()
            else:
                row = connection.execute(
                    """SELECT * FROM solutions WHERE code = ?
                    ORDER BY CASE WHEN manufacturer='SAE/ISO' THEN 0 ELSE 1 END, manufacturer LIMIT 1""",
                    (code,),
                ).fetchone()
        return self._solution(row) if row else None

    def manufacturers(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT manufacturer FROM dtc WHERE is_generic = 0 ORDER BY manufacturer"
            ).fetchall()
        return [row[0] for row in rows]

    def stats(self) -> dict[str, int]:
        with self._connect() as connection:
            definitions = connection.execute("SELECT COUNT(*) FROM dtc").fetchone()[0]
            unique_codes = connection.execute("SELECT COUNT(DISTINCT code) FROM dtc").fetchone()[0]
            manufacturers = connection.execute(
                "SELECT COUNT(DISTINCT manufacturer) FROM dtc WHERE is_generic = 0"
            ).fetchone()[0]
            try:
                solutions = connection.execute("SELECT COUNT(*) FROM solutions").fetchone()[0]
            except sqlite3.OperationalError:
                solutions = 0
        return {
            "definitions": int(definitions), "unique_codes": int(unique_codes),
            "manufacturers": int(manufacturers), "solutions": int(solutions),
        }
