from __future__ import annotations

import io
import re
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

DATASET_URL = "https://github.com/Wal33D/dtc-database/archive/refs/heads/main.zip"
MIN_UNIQUE_CODES = 10_000
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "data" / "autoguard_dtc.sqlite"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.txt"

GENERIC_FILES = {"p_codes", "b_codes", "c_codes", "u_codes", "other_codes"}
MANUFACTURER_NAMES = {
    "acura": "Acura", "audi": "Audi", "bmw": "BMW", "buick": "Buick",
    "cadillac": "Cadillac", "chevy": "Chevrolet", "chrysler": "Chrysler",
    "dodge": "Dodge", "ford": "Ford", "geo": "Geo", "gm": "General Motors",
    "gmc": "GMC", "honda": "Honda", "hyundai": "Hyundai", "infiniti": "Infiniti",
    "isuzu": "Isuzu", "jaguar": "Jaguar", "jeep": "Jeep", "kia": "Kia",
    "land_rover": "Land Rover", "lexus": "Lexus", "lincoln": "Lincoln",
    "mazda": "Mazda", "mercedes": "Mercedes-Benz", "mercury": "Mercury",
    "mini": "MINI", "mitsubishi": "Mitsubishi", "nissan": "Nissan",
    "oldsmobile": "Oldsmobile", "plymouth": "Plymouth", "pontiac": "Pontiac",
    "saab": "Saab", "saturn": "Saturn", "subaru": "Subaru", "suzuki": "Suzuki",
    "toyota": "Toyota", "volkswagen": "Volkswagen", "volvo": "Volvo",
}

LINE_PATTERN = re.compile(r"^\s*([PBCU][0-9A-Fa-f]{4})\s*(?:-|:|\t)\s*(.+?)\s*$")


def download_dataset() -> bytes:
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "AUTOGUARD-SCAN-DIOS-build/6.2"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def normalize_manufacturer(stem: str) -> tuple[str, int]:
    key = stem.lower().removesuffix("_codes")
    if stem.lower() in GENERIC_FILES:
        return "SAE/ISO", 1
    return MANUFACTURER_NAMES.get(key, key.replace("_", " ").title()), 0


def parse_archive(content: bytes) -> list[tuple[str, str, str, int, str]]:
    rows: list[tuple[str, str, str, int, str]] = []
    seen: set[tuple[str, str, str]] = set()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        candidates = [
            name for name in archive.namelist()
            if "/data/source-data/" in name and name.lower().endswith("_codes.txt")
        ]
        if not candidates:
            raise RuntimeError("El repositorio DTC no contiene archivos source-data/*_codes.txt")
        for name in sorted(candidates):
            stem = Path(name).stem
            manufacturer, generic = normalize_manufacturer(stem)
            text = archive.read(name).decode("utf-8", errors="replace")
            for raw_line in text.splitlines():
                match = LINE_PATTERN.match(raw_line)
                if not match:
                    continue
                code = match.group(1).upper()
                description = " ".join(match.group(2).split())
                if not description:
                    continue
                key = (code, description.casefold(), manufacturer)
                if key in seen:
                    continue
                seen.add(key)
                rows.append((code, description, manufacturer, generic, "Wal33D/dtc-database MIT"))
    return rows


def system_from_code(code: str) -> str:
    return {
        "P": "Tren motriz / emisiones",
        "B": "Carrocería y confort",
        "C": "Chasis, frenos y dirección",
        "U": "Comunicación y red de módulos",
    }.get(code[:1], "Sistema no identificado")


def severity_for(code: str, description: str) -> str:
    text = description.casefold()
    critical = ("brake", "airbag", "steering", "overheat", "oil pressure", "no communication", "lost communication")
    high = ("misfire", "lean", "rich", "fuel pressure", "catalyst", "voltage low", "sensor circuit")
    if code.startswith(("C", "B0")) or any(word in text for word in critical):
        return "Alta"
    if code.startswith("U") or any(word in text for word in high):
        return "Media-Alta"
    return "Media"


CURATED: dict[str, dict[str, str]] = {
    "U0123": {
        "severity": "Alta",
        "symptoms": "Testigos ABS/ESC encendidos; control de estabilidad deshabilitado; códigos de comunicación en otros módulos.",
        "causes": "Falta de alimentación o masa del sensor de guiñada; conector suelto u oxidado; circuito CAN High/Low abierto o en corto; batería con voltaje inestable; sensor o módulo defectuoso.",
        "steps": "1. Realizar escaneo completo de todos los módulos y guardar evidencia.\n2. Verificar voltaje de batería y estado de carga.\n3. Revisar fusibles, alimentación y masa del sensor de guiñada.\n4. Inspeccionar conectores por humedad, corrosión o terminales abiertos.\n5. Medir continuidad y posibles cortos en CAN High y CAN Low con el sistema desenergizado.\n6. Verificar resistencia de terminación de la red según procedimiento OEM.\n7. Restablecer conectores, borrar códigos y repetir escaneo.\n8. Si se reemplaza o interviene el sensor, ejecutar calibración de punto cero según fabricante.",
        "validation": "Confirmar comunicación estable con ABS/ESC, ausencia de U0123 después de ciclo de conducción y calibración aceptada.",
        "sensors": "Voltaje módulo; estado de red CAN; ángulo de dirección; aceleración lateral; velocidad de guiñada.",
        "tools": "Multímetro, escáner con acceso ABS/ESC, diagrama eléctrico OEM y, cuando corresponda, osciloscopio CAN.",
    },
    "P0171": {
        "severity": "Media-Alta",
        "symptoms": "Ralentí inestable, pérdida de potencia, tironeos, consumo irregular y MIL encendida.",
        "causes": "Entrada de aire no medida, fuga de vacío, MAF contaminado, baja presión de combustible, inyector restringido, fuga de escape antes del O2.",
        "steps": "1. Registrar STFT/LTFT, MAF, MAP y O2 antes de borrar.\n2. Inspeccionar ductos, PCV, múltiple y mangueras de vacío.\n3. Ejecutar prueba de humo si está disponible.\n4. Comparar MAF en ralentí y bajo carga con cilindrada y referencia OEM.\n5. Medir presión y caudal de combustible.\n6. Revisar inyectores y fugas de escape.\n7. Reparar la causa confirmada, reiniciar adaptativos si el fabricante lo exige y repetir prueba.",
        "validation": "STFT y LTFT estables dentro del rango OEM, ralentí uniforme y ausencia del código tras ciclo de conducción.",
        "sensors": "STFT, LTFT, MAF, MAP, O2/A/F, presión de combustible, RPM y carga calculada.",
        "tools": "Escáner, máquina de humo, manómetro de combustible, multímetro y documentación OEM.",
    },
    "P0300": {
        "severity": "Alta",
        "symptoms": "Motor inestable, pérdida de potencia, vibración, MIL fija o parpadeante y posible daño al catalizador.",
        "causes": "Encendido, inyección, compresión, sincronización, mezcla aire/combustible o fallas mecánicas.",
        "steps": "1. No mantener el motor bajo carga si la MIL parpadea.\n2. Leer contadores de fallas por cilindro y freeze frame.\n3. Revisar bujías, bobinas, conectores y alimentación.\n4. Intercambiar componentes solo como prueba controlada y registrar el resultado.\n5. Comprobar presión de combustible e inyectores.\n6. Medir compresión y fuga de cilindros cuando corresponda.\n7. Verificar sincronización CKP/CMP con equipo adecuado.\n8. Reparar, borrar códigos y confirmar bajo las condiciones del freeze frame.",
        "validation": "Contadores de misfire en cero o dentro de especificación, marcha estable y ausencia de P0300 después de prueba controlada.",
        "sensors": "RPM, carga, trims, MAF, MAP, avance, O2/A/F, presión de combustible y contadores de misfire OEM.",
        "tools": "Escáner, probador de chispa, multímetro, manómetro, compresímetro y osciloscopio físico cuando corresponda.",
    },
    "P0420": {
        "severity": "Media-Alta",
        "symptoms": "MIL encendida; emisiones elevadas; ocasional pérdida de rendimiento.",
        "causes": "Catalizador degradado, mezcla incorrecta, misfire previo, consumo de aceite/refrigerante, sensor O2 lento o fuga de escape.",
        "steps": "1. Resolver primero misfire y códigos de mezcla.\n2. Inspeccionar fugas de escape antes y cerca del catalizador.\n3. Registrar sensores O2/A/F antes y después del catalizador.\n4. Verificar temperatura de entrada y salida bajo procedimiento seguro.\n5. Confirmar consumo de aceite o refrigerante.\n6. Comparar eficiencia con procedimiento OEM antes de reemplazar componentes.",
        "validation": "Monitores de catalizador completos, señales coherentes y ausencia de P0420 tras ciclo de conducción OEM.",
        "sensors": "O2/A/F B1S1 y B1S2, temperatura catalizador, trims, MAF, MAP y misfire.",
        "tools": "Escáner con gráficos, termómetro adecuado, detector de fugas y documentación OEM.",
    },
}


def generic_solution(code: str, description: str, manufacturer: str) -> tuple[str, str, str, str, str, str, str, str]:
    text = description.casefold()
    system = system_from_code(code)
    severity = severity_for(code, description)
    if code.startswith("U"):
        symptoms = "Testigos de advertencia, funciones deshabilitadas y pérdida intermitente o permanente de comunicación entre módulos."
        causes = "Alimentación o masa deficiente; batería inestable; conectores; cableado CAN/LIN; terminaciones de red; módulo sin comunicación."
        steps = "1. Guardar todos los códigos y estados de módulo.\n2. Verificar batería, fusibles, alimentaciones y masas.\n3. Inspeccionar conectores y mazos en zonas de roce o humedad.\n4. Revisar otros códigos U para identificar el módulo común.\n5. Medir la red con procedimientos y diagramas OEM.\n6. Reparar cableado o alimentación antes de condenar un módulo.\n7. Borrar códigos y repetir escaneo completo."
        validation = "Todos los módulos comunican, no reaparece el DTC y las funciones relacionadas operan correctamente."
        sensors = "Voltaje de módulo, estado de comunicación, contadores de errores y parámetros del sistema afectado."
        tools = "Escáner multimódulo, multímetro, diagrama OEM y osciloscopio CAN cuando sea necesario."
    elif code.startswith("C"):
        symptoms = "Testigos ABS/ESC/dirección, función de chasis limitada, comportamiento anormal o código almacenado."
        causes = "Sensor o actuador, alimentación/masa, conector, cableado, señal fuera de rango, calibración o falla mecánica."
        steps = "1. Leer todos los módulos de chasis y guardar freeze frame.\n2. Inspeccionar neumáticos, rodamientos, conectores y cableado.\n3. Comparar sensores relacionados en datos en vivo.\n4. Verificar alimentación, masa y continuidad.\n5. Realizar pruebas activas o calibración únicamente con procedimiento OEM.\n6. Reparar la causa confirmada y repetir prueba de ruta segura."
        validation = "Sin testigos, datos coherentes entre sensores y ausencia del código tras prueba de ruta."
        sensors = "Velocidades de rueda, ángulo de dirección, aceleraciones, presión y señales específicas del sistema."
        tools = "Escáner ABS/ESC, multímetro, equipo de medición y documentación OEM."
    elif code.startswith("B"):
        symptoms = "Función de carrocería o confort inoperativa, testigo, mensaje de advertencia o código histórico."
        causes = "Fusible, alimentación/masa, interruptor, actuador, sensor, conector, cableado o comunicación de módulo."
        steps = "1. Confirmar la función afectada y guardar códigos.\n2. Revisar fusibles y alimentación del módulo.\n3. Inspeccionar conectores y cableado.\n4. Comparar estados de entradas y salidas en datos en vivo.\n5. Ejecutar prueba activa solo cuando el fabricante la autorice.\n6. Reparar y confirmar varios ciclos de funcionamiento."
        validation = "La función opera normalmente y el código no reaparece después de varios ciclos."
        sensors = "Estados de interruptores, voltaje de módulo y entradas/salidas del sistema afectado."
        tools = "Escáner de carrocería, multímetro y diagrama OEM."
    else:
        symptoms = "MIL encendida, rendimiento alterado, consumo elevado, marcha irregular o código almacenado sin síntomas evidentes."
        causes = "Sensor/actuador, alimentación, masa, conector, cableado, fuga, condición mecánica o señal fuera de especificación."
        if "circuit" in text or "sensor" in text:
            causes = "Circuito abierto o en corto, referencia de 5 V, masa, conector, cableado, sensor o módulo de control."
        steps = "1. Registrar DTC, estado, freeze frame y parámetros relacionados.\n2. Consultar diagramas y especificaciones OEM para el vehículo exacto.\n3. Realizar inspección visual de conectores, mazos, mangueras y componentes.\n4. Comparar datos en vivo y rangos esperados.\n5. Verificar alimentación, masa y señal con instrumentos adecuados.\n6. Confirmar la falla antes de sustituir componentes.\n7. Reparar, borrar códigos y repetir las condiciones del freeze frame."
        validation = "Parámetros dentro de especificación, monitores completados y DTC ausente después de la prueba."
        sensors = "PID y sensores relacionados con la descripción del código; trims, carga, voltaje y temperatura cuando corresponda."
        tools = "Escáner, multímetro, herramientas de prueba del sistema y documentación OEM."
    caution = f"Procedimiento orientativo offline para {manufacturer}. Confirmar conectores, valores y secuencias con información OEM del vehículo."
    return system, severity, symptoms, causes, steps, validation, sensors, tools + "\n" + caution


def build_database(rows: list[tuple[str, str, str, int, str]]) -> dict[str, int]:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        OUTPUT.unlink()
    with sqlite3.connect(OUTPUT) as connection:
        connection.executescript(
            """
            PRAGMA journal_mode=DELETE;
            PRAGMA synchronous=FULL;
            CREATE TABLE dtc (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL,
                description TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                is_generic INTEGER NOT NULL CHECK(is_generic IN (0, 1)),
                source TEXT NOT NULL,
                UNIQUE(code, description, manufacturer)
            );
            CREATE INDEX idx_dtc_code ON dtc(code);
            CREATE INDEX idx_dtc_manufacturer ON dtc(manufacturer);
            CREATE INDEX idx_dtc_description ON dtc(description);
            CREATE TABLE solutions (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                system TEXT NOT NULL,
                severity TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                causes TEXT NOT NULL,
                steps TEXT NOT NULL,
                validation TEXT NOT NULL,
                sensors TEXT NOT NULL,
                tools TEXT NOT NULL,
                source TEXT NOT NULL,
                UNIQUE(code, manufacturer)
            );
            CREATE INDEX idx_solution_code ON solutions(code);
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        connection.executemany(
            "INSERT INTO dtc(code, description, manufacturer, is_generic, source) VALUES (?, ?, ?, ?, ?)", rows
        )
        solution_rows: list[tuple[str, str, str, str, str, str, str, str, str, str, str]] = []
        seen_solution: set[tuple[str, str]] = set()
        for code, description, manufacturer, _generic, _source in rows:
            key = (code, manufacturer)
            if key in seen_solution:
                continue
            seen_solution.add(key)
            system, severity, symptoms, causes, steps, validation, sensors, tools = generic_solution(code, description, manufacturer)
            if code in CURATED:
                curated = CURATED[code]
                severity = curated.get("severity", severity)
                symptoms = curated.get("symptoms", symptoms)
                causes = curated.get("causes", causes)
                steps = curated.get("steps", steps)
                validation = curated.get("validation", validation)
                sensors = curated.get("sensors", sensors)
                tools = curated.get("tools", tools)
            solution_rows.append((
                code, manufacturer, system, severity, symptoms, causes, steps,
                validation, sensors, tools, "AUTOGUARD offline knowledge base 2026.07"
            ))
        connection.executemany(
            """INSERT INTO solutions(
                code, manufacturer, system, severity, symptoms, causes, steps,
                validation, sensors, tools, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            solution_rows,
        )
        unique_codes = connection.execute("SELECT COUNT(DISTINCT code) FROM dtc").fetchone()[0]
        definitions = connection.execute("SELECT COUNT(*) FROM dtc").fetchone()[0]
        manufacturers = connection.execute("SELECT COUNT(DISTINCT manufacturer) FROM dtc WHERE is_generic = 0").fetchone()[0]
        solutions = connection.execute("SELECT COUNT(*) FROM solutions").fetchone()[0]
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [
                ("schema_version", "2"), ("dataset", "Wal33D/dtc-database"),
                ("license", "MIT"), ("unique_codes", str(unique_codes)),
                ("definitions", str(definitions)), ("manufacturers", str(manufacturers)),
                ("solutions", str(solutions)),
            ],
        )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity_check: {integrity}")
    if unique_codes < MIN_UNIQUE_CODES:
        raise RuntimeError(f"Base incompleta: {unique_codes} códigos únicos; se esperaban al menos {MIN_UNIQUE_CODES}")
    with sqlite3.connect(OUTPUT) as connection:
        u0123 = connection.execute("SELECT COUNT(*) FROM dtc WHERE code='U0123'").fetchone()[0]
        u0123_solution = connection.execute("SELECT COUNT(*) FROM solutions WHERE code='U0123'").fetchone()[0]
    if not u0123 or not u0123_solution:
        raise RuntimeError("La base generada no contiene U0123 y su plan de acción")
    return {
        "unique_codes": int(unique_codes), "definitions": int(definitions),
        "manufacturers": int(manufacturers), "solutions": int(solutions),
    }


def write_notice() -> None:
    notice = """AUTOGUARD SCAN DIOS v6.2 — AVISOS DE TERCEROS

Base de definiciones DTC: Wal33D/dtc-database
Copyright (c) 2024 Wal33D (Waleed Judah)

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Los planes de acción y procedimientos AUTOGUARD son material técnico orientativo
offline y deben confirmarse con información OEM, inspección y mediciones del
vehículo exacto antes de reemplazar componentes.
"""
    NOTICES.write_text(notice, encoding="utf-8")


def main() -> None:
    content = download_dataset()
    rows = parse_archive(content)
    stats = build_database(rows)
    write_notice()
    print(
        "Base DTC creada:", f"{stats['unique_codes']} códigos únicos,",
        f"{stats['definitions']} definiciones,", f"{stats['manufacturers']} fabricantes,",
        f"{stats['solutions']} planes offline",
    )


if __name__ == "__main__":
    main()
