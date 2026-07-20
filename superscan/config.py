from __future__ import annotations

from pathlib import Path
import os

APP_NAME = "SuperScan 2.0 Profesional"
APP_VERSION = "2.1.0"
APP_PUBLISHER = "AutoGuard Servicios"
AUTHOR = "Esteban Cortez"

LOCAL_APPDATA = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
APP_DATA_DIR = LOCAL_APPDATA / "SuperScan" / "2.0 Final Mejorado"
LOG_FILE = APP_DATA_DIR / "SuperScan_2.0_runtime.log"
DB_FILE = APP_DATA_DIR / "superscan_dtc.sqlite3"
REPORT_DIR = Path.home() / "Documents" / "AutoGuard" / "SuperScan" / "Informes"

APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "nav": "#071B2F",
    "nav_hover": "#102B47",
    "primary": "#0B74D1",
    "primary_dark": "#075BA5",
    "accent": "#FF7A00",
    "success": "#19A974",
    "warning": "#E6A700",
    "danger": "#D83A3A",
    "surface": "#FFFFFF",
    "surface_alt": "#F3F6F9",
    "border": "#D5DEE8",
    "text": "#17212B",
    "muted": "#66788A",
    "console": "#0A121A",
}

PID_DEFINITIONS = {
    "0104": ("Carga calculada", "%", lambda a, b=0: a * 100.0 / 255.0),
    "0105": ("Temperatura refrigerante", "°C", lambda a, b=0: a - 40.0),
    "0106": ("Ajuste combustible corto B1", "%", lambda a, b=0: a * 100.0 / 128.0 - 100.0),
    "0107": ("Ajuste combustible largo B1", "%", lambda a, b=0: a * 100.0 / 128.0 - 100.0),
    "010B": ("Presión MAP", "kPa", lambda a, b=0: float(a)),
    "010C": ("RPM motor", "rpm", lambda a, b: (256.0 * a + b) / 4.0),
    "010D": ("Velocidad", "km/h", lambda a, b=0: float(a)),
    "010E": ("Avance de encendido", "°", lambda a, b=0: a / 2.0 - 64.0),
    "010F": ("Temperatura admisión", "°C", lambda a, b=0: a - 40.0),
    "0110": ("Flujo de aire MAF", "g/s", lambda a, b: (256.0 * a + b) / 100.0),
    "0111": ("Posición acelerador", "%", lambda a, b=0: a * 100.0 / 255.0),
    "0114": ("Sensor O2 B1S1", "V", lambda a, b=0: a / 200.0),
    "011F": ("Tiempo desde arranque", "s", lambda a, b: 256.0 * a + b),
    "0123": ("Presión riel combustible", "kPa", lambda a, b: (256.0 * a + b) * 10.0),
    "012E": ("Comando purga EVAP", "%", lambda a, b=0: a * 100.0 / 255.0),
    "012F": ("Nivel de combustible", "%", lambda a, b=0: a * 100.0 / 255.0),
    "0133": ("Presión barométrica", "kPa", lambda a, b=0: float(a)),
    "0142": ("Voltaje módulo control", "V", lambda a, b: (256.0 * a + b) / 1000.0),
    "0146": ("Temperatura ambiente", "°C", lambda a, b=0: a - 40.0),
    "015E": ("Caudal de combustible", "L/h", lambda a, b: (256.0 * a + b) / 20.0),
}

LIVE_PID_ORDER = [
    "010C", "010D", "0105", "010F", "0111", "0104", "010B", "0110",
    "0106", "0107", "010E", "0114", "015E", "012F", "0133", "011F",
    "0142", "0146", "012E",
]

PROTOCOL_NAMES = {
    "0": "Automático",
    "1": "SAE J1850 PWM",
    "2": "SAE J1850 VPW",
    "3": "ISO 9141-2",
    "4": "ISO 14230-4 KWP (5 baud)",
    "5": "ISO 14230-4 KWP (inicio rápido)",
    "6": "ISO 15765-4 CAN (11 bit, 500 kbaud)",
    "7": "ISO 15765-4 CAN (29 bit, 500 kbaud)",
    "8": "ISO 15765-4 CAN (11 bit, 250 kbaud)",
    "9": "ISO 15765-4 CAN (29 bit, 250 kbaud)",
    "A": "SAE J1939 CAN",
}
