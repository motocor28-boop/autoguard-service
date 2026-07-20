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
    "acura": "Acura",
    "audi": "Audi",
    "bmw": "BMW",
    "buick": "Buick",
    "cadillac": "Cadillac",
    "chevy": "Chevrolet",
    "chrysler": "Chrysler",
    "dodge": "Dodge",
    "ford": "Ford",
    "geo": "Geo",
    "gm": "General Motors",
    "gmc": "GMC",
    "honda": "Honda",
    "hyundai": "Hyundai",
    "infiniti": "Infiniti",
    "isuzu": "Isuzu",
    "jaguar": "Jaguar",
    "jeep": "Jeep",
    "kia": "Kia",
    "land_rover": "Land Rover",
    "lexus": "Lexus",
    "lincoln": "Lincoln",
    "mazda": "Mazda",
    "mercedes": "Mercedes-Benz",
    "mercury": "Mercury",
    "mini": "MINI",
    "mitsubishi": "Mitsubishi",
    "nissan": "Nissan",
    "oldsmobile": "Oldsmobile",
    "plymouth": "Plymouth",
    "pontiac": "Pontiac",
    "saab": "Saab",
    "saturn": "Saturn",
    "subaru": "Subaru",
    "suzuki": "Suzuki",
    "toyota": "Toyota",
    "volkswagen": "Volkswagen",
    "volvo": "Volvo",
}

LINE_PATTERN = re.compile(r"^\s*([PBCU][0-9A-Fa-f]{4})\s*(?:-|:|\t)\s*(.+?)\s*$")


def download_dataset() -> bytes:
    request = urllib.request.Request(
        DATASET_URL,
        headers={"User-Agent": "AUTOGUARD-SCAN-DIOS-build/6.2"},
    )
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
            name
            for name in archive.namelist()
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
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        connection.executemany(
            "INSERT INTO dtc(code, description, manufacturer, is_generic, source) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        unique_codes = connection.execute("SELECT COUNT(DISTINCT code) FROM dtc").fetchone()[0]
        definitions = connection.execute("SELECT COUNT(*) FROM dtc").fetchone()[0]
        manufacturers = connection.execute(
            "SELECT COUNT(DISTINCT manufacturer) FROM dtc WHERE is_generic = 0"
        ).fetchone()[0]
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [
                ("schema_version", "1"),
                ("dataset", "Wal33D/dtc-database"),
                ("license", "MIT"),
                ("unique_codes", str(unique_codes)),
                ("definitions", str(definitions)),
                ("manufacturers", str(manufacturers)),
            ],
        )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity_check: {integrity}")
    if unique_codes < MIN_UNIQUE_CODES:
        raise RuntimeError(
            f"Base incompleta: {unique_codes} códigos únicos; se esperaban al menos {MIN_UNIQUE_CODES}"
        )
    with sqlite3.connect(OUTPUT) as connection:
        u0123 = connection.execute("SELECT COUNT(*) FROM dtc WHERE code='U0123'").fetchone()[0]
    if not u0123:
        raise RuntimeError("La base generada no contiene U0123")
    return {
        "unique_codes": int(unique_codes),
        "definitions": int(definitions),
        "manufacturers": int(manufacturers),
    }


def write_notice() -> None:
    NOTICES.write_text(
        """AUTOGUARD SCAN DIOS v6.2 — AVISOS DE TERCEROS\n\n"
        "Base de definiciones DTC: Wal33D/dtc-database\n"
        "Copyright (c) 2024 Wal33D (Waleed Judah)\n\n"
        "MIT License\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
        "of this software and associated documentation files (the \"Software\"), to deal\n"
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n\n"
        "The above copyright notice and this permission notice shall be included in all\n"
        "copies or substantial portions of the Software.\n\n"
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
        "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
        "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
        "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
        "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
        "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
        "SOFTWARE.\n",
        encoding="utf-8",
    )


def main() -> None:
    content = download_dataset()
    rows = parse_archive(content)
    stats = build_database(rows)
    write_notice()
    print(
        "Base DTC creada:",
        f"{stats['unique_codes']} códigos únicos,",
        f"{stats['definitions']} definiciones,",
        f"{stats['manufacturers']} fabricantes",
    )


if __name__ == "__main__":
    main()
