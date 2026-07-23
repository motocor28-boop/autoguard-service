from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from core import ELM327Client, PID_DEFINITIONS, parse_pid_value


ProgressCallback = Callable[[int, str], None]


@dataclass(slots=True)
class ECUIdentifier:
    response_header: str
    request_header: str
    family: str
    vin: str = ""
    serial_number: str = ""
    software_number: str = ""
    uds_dtcs: list[str] = field(default_factory=list)
    raw: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DeepScanResult:
    started_at: float
    finished_at: float = 0.0
    protocol: str = ""
    adapter: dict[str, str] = field(default_factory=dict)
    readiness: dict[str, object] = field(default_factory=dict)
    supported_pids: list[int] = field(default_factory=list)
    live_values: dict[str, dict[str, object]] = field(default_factory=dict)
    freeze_frame: dict[str, dict[str, object]] = field(default_factory=dict)
    vehicle_information: dict[str, str] = field(default_factory=dict)
    dtcs: dict[str, list[str]] = field(default_factory=dict)
    mode06_tests: list[str] = field(default_factory=list)
    modules: list[ECUIdentifier] = field(default_factory=list)
    raw_responses: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["duration_seconds"] = round(max(0.0, self.finished_at - self.started_at), 2)
        return data

    def save_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path


OBD_STANDARD = {
    1: "OBD-II CARB",
    2: "OBD EPA",
    3: "OBD y OBD-II",
    4: "OBD-I",
    5: "No compatible OBD",
    6: "EOBD",
    7: "EOBD y OBD-II",
    8: "EOBD y OBD",
    9: "EOBD, OBD y OBD-II",
    10: "JOBD",
    11: "JOBD y OBD-II",
    12: "JOBD y EOBD",
    13: "JOBD, EOBD y OBD-II",
    17: "EMD",
    18: "EMD+",
    19: "HD OBD-C",
    20: "HD OBD",
    21: "WWH OBD",
    23: "HD EOBD-I",
    24: "HD EOBD-I N",
    25: "HD EOBD-II",
    26: "HD EOBD-II N",
    28: "OBDBr-1",
    29: "OBDBr-2",
    30: "KOBD",
    31: "IOBD I",
    32: "IOBD II",
    33: "HD EOBD-IV",
}

FUEL_TYPE = {
    1: "Gasolina", 2: "Metanol", 3: "Etanol", 4: "Diésel", 5: "GLP",
    6: "GNC", 7: "Propano", 8: "Eléctrico", 9: "Bifuel gasolina",
    10: "Bifuel metanol", 11: "Bifuel etanol", 12: "Bifuel GLP",
    13: "Bifuel GNC", 14: "Bifuel propano", 15: "Bifuel eléctrico",
    16: "Bifuel eléctrico/combustión", 17: "Híbrido gasolina",
    18: "Híbrido etanol", 19: "Híbrido diésel", 20: "Híbrido eléctrico",
    21: "Híbrido mixto", 22: "Híbrido regenerativo", 23: "Bifuel diésel",
}

MODULE_NAMES = {
    "7E0": "Motor / PCM",
    "7E1": "Transmisión / TCM",
    "7E2": "Sistema híbrido / energía",
    "7E3": "Módulo auxiliar 1",
    "7E4": "Módulo auxiliar 2",
    "7E5": "Módulo auxiliar 3",
    "7E6": "Módulo auxiliar 4",
    "7E7": "Módulo auxiliar 5",
    "7D0": "Módulo de chasis / ABS (dirección común)",
    "7D1": "Módulo de chasis / ABS (dirección común)",
    "7D2": "Módulo de carrocería (dirección común)",
    "760": "Módulo OEM auxiliar (dirección común)",
}


def _clean_hex(text: str) -> str:
    return re.sub(r"[^0-9A-F]", "", text.upper())


def _extract_after_marker(text: str, marker: str) -> bytes:
    clean = _clean_hex(text)
    marker = marker.upper()
    index = clean.find(marker)
    if index < 0:
        return b""
    payload = clean[index + len(marker):]
    if len(payload) % 2:
        payload = payload[:-1]
    try:
        return bytes.fromhex(payload)
    except ValueError:
        return b""


def _decode_printable(data: bytes) -> str:
    text = "".join(chr(value) if 32 <= value <= 126 else "" for value in data)
    return text.strip(" \x00")


def _mode01_bytes(response: str, pid: int) -> bytes:
    return _extract_after_marker(response, f"41{pid:02X}")


def _mode02_bytes(response: str, pid: int) -> bytes:
    return _extract_after_marker(response, f"42{pid:02X}")


def parse_readiness(response: str) -> dict[str, object]:
    data = _mode01_bytes(response, 0x01)
    if len(data) < 4:
        return {"raw": response.strip(), "available": False}
    a, b, c, d = data[:4]
    compression = bool(b & 0x08)
    continuous = {
        "Falla de encendido": {"soportado": bool(b & 0x01), "incompleto": bool(b & 0x10)},
        "Sistema de combustible": {"soportado": bool(b & 0x02), "incompleto": bool(b & 0x20)},
        "Componentes integrales": {"soportado": bool(b & 0x04), "incompleto": bool(b & 0x40)},
    }
    if compression:
        labels = ["Catalizador NMHC", "NOx/SCR", "Boost", "Reservado", "Filtro particulado", "EGR/VVT", "Reservado", "Reservado"]
    else:
        labels = ["Catalizador", "Catalizador calentado", "EVAP", "Aire secundario", "A/C refrigerante", "Sensor O2", "Calentador O2", "EGR/VVT"]
    non_continuous: dict[str, dict[str, bool]] = {}
    for bit, label in enumerate(labels):
        non_continuous[label] = {"soportado": bool(c & (1 << bit)), "incompleto": bool(d & (1 << bit))}
    return {
        "available": True,
        "mil_encendida": bool(a & 0x80),
        "cantidad_dtc_confirmados": a & 0x7F,
        "tipo_encendido": "Compresión" if compression else "Chispa",
        "monitores_continuos": continuous,
        "monitores_no_continuos": non_continuous,
        "raw_bytes": data[:4].hex(" ").upper(),
    }


def discover_headers(response: str) -> list[tuple[str, str, str]]:
    found: dict[str, tuple[str, str, str]] = {}
    for line in response.upper().splitlines():
        match = re.match(r"\s*([0-9A-F]{3}|[0-9A-F]{8})\s+", line)
        if not match:
            continue
        header = match.group(1)
        if len(header) == 3:
            value = int(header, 16)
            if 0x7E8 <= value <= 0x7EF:
                request = f"{value - 8:03X}"
                found[header] = (header, request, MODULE_NAMES.get(request, "ECU OBD-II CAN"))
        elif header.startswith("18DAF1"):
            source = header[-2:]
            request = f"18DA{source}F1"
            found[header] = (header, request, f"ECU UDS 29-bit · dirección {source}")
    return list(found.values())


def parse_uds_ascii(response: str, did: str) -> str:
    data = _extract_after_marker(response, f"62{did}")
    return _decode_printable(data)


def parse_uds_dtcs(response: str) -> list[str]:
    data = _extract_after_marker(response, "5902")
    if len(data) < 2:
        return []
    # First byte is commonly the DTC status availability mask.
    payload = data[1:]
    codes: list[str] = []
    for index in range(0, len(payload) - 3, 4):
        dtc = payload[index:index + 3].hex().upper()
        status = payload[index + 3]
        if dtc != "000000":
            codes.append(f"{dtc} · estado 0x{status:02X}")
    return codes


class DeepScanner:
    """Read-only scan of standard OBD-II and safe diagnostic identification data.

    It never clears DTCs, changes coding, performs actuations, flashes modules or
    enters programming sessions. Proprietary values remain OEM-dependent.
    """

    COMMON_READ_ONLY_HEADERS = [
        "7E0", "7E1", "7E2", "7E3", "7E4", "7E5", "7E6", "7E7",
        "7D0", "7D1", "7D2", "760", "761", "762",
    ]

    def __init__(self, client: ELM327Client, progress: ProgressCallback | None = None) -> None:
        self.client = client
        self.progress = progress or (lambda _value, _message: None)

    def _step(self, value: int, message: str) -> None:
        self.progress(max(0, min(100, value)), message)

    def _command(self, result: DeepScanResult, key: str, command: str, timeout: float = 3.0) -> str:
        try:
            response = self.client.command(command, timeout=timeout)
        except Exception as exc:
            response = f"ERROR: {exc}"
        result.raw_responses[key] = response
        return response

    def _supported_pids(self, result: DeepScanResult) -> list[int]:
        supported: set[int] = set()
        for base in range(0x00, 0x100, 0x20):
            response = self._command(result, f"PID_BLOCK_{base:02X}", f"01{base:02X}")
            data = _mode01_bytes(response, base)
            if len(data) < 4:
                continue
            mask = int.from_bytes(data[:4], "big")
            for bit in range(32):
                if mask & (1 << (31 - bit)):
                    supported.add(base + bit + 1)
            if not (mask & 0x1):
                break
        return sorted(pid for pid in supported if pid <= 0xFF)

    def _vehicle_info(self, result: DeepScanResult) -> None:
        queries = {
            "VIN": ("0902", "4902", True),
            "ID de calibración": ("0904", "4904", True),
            "CVN": ("0906", "4906", False),
            "Nombre ECU": ("090A", "490A", True),
        }
        for label, (command, marker, ascii_value) in queries.items():
            response = self._command(result, f"MODE09_{command}", command, timeout=5.0)
            data = _extract_after_marker(response, marker)
            if not data:
                continue
            # Mode 09 responses can contain message counters. Preserve printable
            # characters and remove control/index bytes.
            if ascii_value:
                value = _decode_printable(data)
            else:
                value = data.hex(" ").upper()
            if value:
                result.vehicle_information[label] = value

    def _standard_values(self, result: DeepScanResult) -> None:
        for pid in result.supported_pids:
            if pid not in PID_DEFINITIONS:
                continue
            response = self._command(result, f"PID_{pid:02X}", f"01{pid:02X}")
            data = _mode01_bytes(response, pid)
            try:
                value = parse_pid_value(pid, data)
            except Exception:
                continue
            name, unit = PID_DEFINITIONS[pid]
            result.live_values[f"01{pid:02X}"] = {"name": name, "value": value, "unit": unit}

        obd_response = self._command(result, "OBD_STANDARD", "011C")
        obd_data = _mode01_bytes(obd_response, 0x1C)
        if obd_data:
            result.vehicle_information["Norma OBD"] = OBD_STANDARD.get(obd_data[0], f"Valor 0x{obd_data[0]:02X}")
        fuel_response = self._command(result, "FUEL_TYPE", "0151")
        fuel_data = _mode01_bytes(fuel_response, 0x51)
        if fuel_data:
            result.vehicle_information["Tipo de combustible ECU"] = FUEL_TYPE.get(fuel_data[0], f"Valor 0x{fuel_data[0]:02X}")

    def _freeze_frame(self, result: DeepScanResult) -> None:
        # Query every implemented PID announced by the ECU. Some ECUs answer only
        # when a freeze frame exists; missing responses are normal.
        for pid in result.supported_pids:
            if pid not in PID_DEFINITIONS:
                continue
            response = self._command(result, f"FREEZE_{pid:02X}", f"02{pid:02X}")
            data = _mode02_bytes(response, pid)
            try:
                value = parse_pid_value(pid, data)
            except Exception:
                continue
            name, unit = PID_DEFINITIONS[pid]
            result.freeze_frame[f"02{pid:02X}"] = {"name": name, "value": value, "unit": unit}

    def _mode06(self, result: DeepScanResult) -> None:
        response = self._command(result, "MODE06", "06", timeout=8.0)
        payloads: list[str] = []
        for line in response.upper().splitlines():
            clean = _clean_hex(line)
            marker = clean.find("46")
            if marker >= 0:
                payload = clean[marker + 2:]
                if payload and payload not in payloads:
                    payloads.append(payload)
        result.mode06_tests = payloads
        if payloads:
            result.warnings.append(
                "Mode 06 fue capturado en formato crudo. La interpretación MID/TID/CID y límites depende del fabricante y la norma implementada por la ECU."
            )

    def _discover_modules(self, result: DeepScanResult) -> list[ECUIdentifier]:
        self._command(result, "HEADERS_ON", "ATH1")
        response = self._command(result, "MODULE_DISCOVERY_0100", "0100", timeout=5.0)
        discovered = [ECUIdentifier(*item) for item in discover_headers(response)]
        self._command(result, "HEADERS_OFF", "ATH0")
        return discovered

    def _probe_uds_modules(self, result: DeepScanResult, modules: list[ECUIdentifier]) -> None:
        known_requests = {module.request_header for module in modules}
        for header in self.COMMON_READ_ONLY_HEADERS:
            if header not in known_requests:
                modules.append(ECUIdentifier("", header, MODULE_NAMES.get(header, "Módulo OEM sondeado")))
                known_requests.add(header)

        responsive: list[ECUIdentifier] = []
        self._command(result, "UDS_HEADERS_ON", "ATH1")
        for index, module in enumerate(modules):
            progress = 72 + int((index / max(len(modules), 1)) * 17)
            self._step(progress, f"Sondeo UDS de solo lectura: {module.request_header}")
            set_header = self._command(result, f"SET_HEADER_{module.request_header}", f"ATSH{module.request_header}")
            if "ERROR" in set_header.upper() or "?" in set_header:
                continue
            responses = {
                "VIN_F190": self._command(result, f"UDS_{module.request_header}_F190", "22F190", timeout=1.2),
                "SERIAL_F18C": self._command(result, f"UDS_{module.request_header}_F18C", "22F18C", timeout=1.2),
                "SOFTWARE_F189": self._command(result, f"UDS_{module.request_header}_F189", "22F189", timeout=1.2),
                "DTC_1902FF": self._command(result, f"UDS_{module.request_header}_1902FF", "1902FF", timeout=1.5),
            }
            positive = any(marker in _clean_hex(value) for marker, value in (
                ("62F190", responses["VIN_F190"]),
                ("62F18C", responses["SERIAL_F18C"]),
                ("62F189", responses["SOFTWARE_F189"]),
                ("5902", responses["DTC_1902FF"]),
            ))
            if not positive:
                continue
            module.vin = parse_uds_ascii(responses["VIN_F190"], "F190")
            module.serial_number = parse_uds_ascii(responses["SERIAL_F18C"], "F18C")
            module.software_number = parse_uds_ascii(responses["SOFTWARE_F189"], "F189")
            module.uds_dtcs = parse_uds_dtcs(responses["DTC_1902FF"])
            module.raw = responses
            responsive.append(module)
        self._command(result, "RESTORE_FUNCTIONAL_HEADER", "ATSH7DF")
        self._command(result, "UDS_HEADERS_OFF", "ATH0")
        result.modules = responsive or [module for module in modules if module.response_header]

    def run(self) -> DeepScanResult:
        if not self.client.connected:
            raise RuntimeError("No existe conexión activa. Conecte el vehículo o seleccione el simulador.")
        result = DeepScanResult(started_at=time.time(), protocol=self.client.protocol)
        self._step(2, "Identificando adaptador y protocolo")
        for key, command in (("Identificación", "ATI"), ("Protocolo", "ATDP"), ("Código protocolo", "ATDPN"), ("Voltaje adaptador", "ATRV")):
            result.adapter[key] = self._command(result, f"ADAPTER_{command}", command).replace(">", " ").strip()

        self._step(8, "Leyendo MIL, DTC y monitores de preparación")
        readiness_response = self._command(result, "READINESS_0101", "0101")
        result.readiness = parse_readiness(readiness_response)

        self._step(14, "Detectando todos los bloques PID publicados por la ECU")
        result.supported_pids = self._supported_pids(result)

        self._step(24, "Leyendo todos los sensores estándar compatibles")
        self._standard_values(result)

        self._step(39, "Leyendo VIN, calibraciones, CVN y nombre ECU")
        self._vehicle_info(result)

        self._step(48, "Leyendo DTC confirmados, pendientes y permanentes")
        for mode, label in (("03", "confirmados"), ("07", "pendientes"), ("0A", "permanentes")):
            try:
                result.dtcs[label] = self.client.read_dtcs(mode)
            except Exception as exc:
                result.dtcs[label] = []
                result.warnings.append(f"No se pudo leer DTC {label}: {exc}")

        self._step(56, "Recuperando freeze frame disponible")
        self._freeze_frame(result)

        self._step(64, "Capturando pruebas de monitores Mode 06")
        self._mode06(result)

        self._step(70, "Detectando ECU que responden en la red OBD-II")
        modules = self._discover_modules(result)

        self._step(72, "Sondeando identificadores UDS de solo lectura")
        self._probe_uds_modules(result, modules)

        self._step(91, "Consolidando información y respuestas crudas")
        result.warnings.extend([
            "El escaneo es de solo lectura: no borra DTC, no codifica módulos, no acciona componentes y no programa ECU.",
            "No existe un comando universal para leer absolutamente todos los datos propietarios de todas las marcas. Los parámetros OEM requieren definiciones, direcciones y seguridad específicas del fabricante.",
            "ELM327 puede limitar velocidad, tamaño de respuesta y acceso a redes secundarias. Para cobertura OEM completa se requiere hardware J2534/DoIP/CAN-FD y bases de datos del fabricante.",
        ])
        result.finished_at = time.time()
        self._step(100, "Escaneo profundo finalizado")
        return result
