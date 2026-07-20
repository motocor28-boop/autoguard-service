from __future__ import annotations

import math
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

import serial
from serial.tools import list_ports

from .config import LIVE_PID_ORDER, PID_DEFINITIONS


class OBDConnectionError(RuntimeError):
    pass


class OBDProtocolError(RuntimeError):
    pass


class Transport(Protocol):
    def open(self) -> None: ...
    def close(self) -> None: ...
    def query(self, command: str, timeout: float = 3.0) -> str: ...
    @property
    def is_open(self) -> bool: ...


class SerialTransport:
    def __init__(self, port: str, baudrate: int = 38400):
        self.port = port
        self.baudrate = baudrate
        self.serial: serial.Serial | None = None

    @property
    def is_open(self) -> bool:
        return bool(self.serial and self.serial.is_open)

    def open(self) -> None:
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0.15,
                write_timeout=2.0,
            )
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
        except Exception as exc:
            raise OBDConnectionError(f"No fue posible abrir {self.port}: {exc}") from exc

    def close(self) -> None:
        if self.serial:
            try:
                self.serial.close()
            finally:
                self.serial = None

    def query(self, command: str, timeout: float = 3.0) -> str:
        if not self.serial or not self.serial.is_open:
            raise OBDConnectionError("Puerto serial cerrado")
        self.serial.reset_input_buffer()
        self.serial.write((command.strip() + "\r").encode("ascii", errors="ignore"))
        self.serial.flush()
        deadline = time.monotonic() + timeout
        buffer = bytearray()
        while time.monotonic() < deadline:
            chunk = self.serial.read(512)
            if chunk:
                buffer.extend(chunk)
                if b">" in buffer:
                    break
            else:
                time.sleep(0.01)
        return buffer.decode("ascii", errors="ignore")


class WiFiTransport:
    def __init__(self, host: str, port: int = 35000):
        self.host = host
        self.port = int(port)
        self.sock: socket.socket | None = None

    @property
    def is_open(self) -> bool:
        return self.sock is not None

    def open(self) -> None:
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=5.0)
            self.sock.settimeout(0.15)
        except Exception as exc:
            self.sock = None
            raise OBDConnectionError(f"No fue posible conectar a {self.host}:{self.port}: {exc}") from exc

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def query(self, command: str, timeout: float = 3.0) -> str:
        if not self.sock:
            raise OBDConnectionError("Conexión Wi-Fi cerrada")
        self.sock.sendall((command.strip() + "\r").encode("ascii", errors="ignore"))
        deadline = time.monotonic() + timeout
        parts: list[bytes] = []
        while time.monotonic() < deadline:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                break
            parts.append(chunk)
            if b">" in chunk:
                break
        return b"".join(parts).decode("ascii", errors="ignore")


class SimulatorTransport:
    def __init__(self):
        self._open = False
        self.started = time.monotonic()
        self.cleared = False

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        self._open = True
        self.started = time.monotonic()

    def close(self) -> None:
        self._open = False

    @staticmethod
    def _hex16(value: int) -> str:
        value = max(0, min(65535, int(value)))
        return f"{value >> 8:02X} {value & 0xFF:02X}"

    def _live_response(self, command: str) -> str:
        elapsed = time.monotonic() - self.started
        speed = max(0.0, 42.0 + 18.0 * math.sin(elapsed / 8.0))
        rpm = 850.0 + speed * 35.0 + 90.0 * math.sin(elapsed * 1.5)
        coolant = min(92.0, 65.0 + elapsed * 0.25)
        intake = 31.0 + 2.0 * math.sin(elapsed / 7.0)
        throttle = 14.0 + speed / 5.0
        load = 28.0 + speed / 2.5
        maf = 4.8 + rpm / 600.0
        fuel_flow = 2.4 + load * 0.08
        fuel_level = max(8.0, 62.5 - elapsed / 7200.0)
        map_kpa = 30.0 + load * 0.7
        values: dict[str, tuple[int, int | None]] = {
            "0104": (round(load * 255 / 100), None),
            "0105": (round(coolant + 40), None),
            "0106": (127, None),
            "0107": (127, None),
            "010B": (round(map_kpa), None),
            "010C": (round(rpm * 4) >> 8, round(rpm * 4) & 0xFF),
            "010D": (round(speed), None),
            "010E": (154, None),
            "010F": (round(intake + 40), None),
            "0110": (round(maf * 100) >> 8, round(maf * 100) & 0xFF),
            "0111": (round(throttle * 255 / 100), None),
            "0114": (57, 126),
            "011F": (round(elapsed) >> 8, round(elapsed) & 0xFF),
            "0123": (0x0B, 0xB8),
            "012E": (26, None),
            "012F": (round(fuel_level * 255 / 100), None),
            "0133": (101, None),
            "0142": (0x36, 0x48),
            "0146": (71, None),
            "015E": (round(fuel_flow * 20) >> 8, round(fuel_flow * 20) & 0xFF),
        }
        if command not in values:
            return "NO DATA\r>"
        a, b = values[command]
        pid = command[2:]
        payload = f"41 {pid} {a:02X}" + (f" {b:02X}" if b is not None else "")
        return payload + "\r>"

    def query(self, command: str, timeout: float = 3.0) -> str:
        if not self._open:
            raise OBDConnectionError("Simulador cerrado")
        time.sleep(0.025)
        cmd = command.strip().upper().replace(" ", "")
        static = {
            "ATZ": "ELM327 v1.5 SUPERSCAN\r>",
            "ATI": "ELM327 v1.5 SUPERSCAN\r>",
            "ATE0": "OK\r>",
            "ATL0": "OK\r>",
            "ATS1": "OK\r>",
            "ATH0": "OK\r>",
            "ATCAF1": "OK\r>",
            "ATCFC1": "OK\r>",
            "ATAT2": "OK\r>",
            "ATST64": "OK\r>",
            "ATSP0": "OK\r>",
            "ATDPN": "A6\r>",
            "ATDP": "ISO 15765-4 CAN (11 bit ID, 500 kbaud)\r>",
            "0100": "41 00 BE 3E B8 13\r>",
            "0120": "41 20 00 06 20 01\r>",
            "0140": "41 40 44 00 00 04\r>",
            "0160": "41 60 00 00 00 00\r>",
            "0101": "41 01 83 07 65 00\r>",
            "0902": "49 02 01 4B 4C 31 4A 45 42 41 42 30 46 42 30 30 30 30 30 31\r>",
            "ATRV": "13.9V\r>",
            "020200": "42 02 01 33\r>",
            "020C00": "42 0C 0C E8\r>",
            "020D00": "42 0D 03\r>",
            "020500": "42 05 81\r>",
            "020400": "42 04 4D\r>",
        }
        if cmd == "04":
            self.cleared = True
            return "44\r>"
        if cmd == "03":
            return "43 00 00\r>" if self.cleared else "43 01 33 03 00 04 20 00 00\r>"
        if cmd == "07":
            return "47 00 00\r>" if self.cleared else "47 01 71 00 00\r>"
        if cmd == "0A":
            return "4A 00 00\r>" if self.cleared else "4A 04 20 00 00\r>"
        if cmd in static:
            return static[cmd]
        if cmd.startswith("01"):
            return self._live_response(cmd)
        return "NO DATA\r>"


def available_serial_ports() -> list[str]:
    return [port.device for port in list_ports.comports()]


def _normalize_response(raw: str, command: str = "") -> str:
    cmd = command.strip().upper().replace(" ", "")
    parts: list[str] = []
    for line in raw.replace("\x00", "").replace(">", "\n").splitlines():
        text = line.strip().upper()
        compact = text.replace(" ", "")
        if not text or compact == cmd:
            continue
        if text.startswith("SEARCHING") or text.startswith("BUS INIT"):
            continue
        parts.append(text)
    return " ".join(parts).strip()


def _hex_bytes(text: str) -> list[int]:
    return [int(token, 16) for token in re.findall(r"(?<![0-9A-F])[0-9A-F]{2}(?![0-9A-F])", text.upper())]


def parse_dtc_bytes(data: Iterable[int]) -> list[str]:
    values = list(data)
    codes: list[str] = []
    for i in range(0, len(values) - 1, 2):
        a, b = values[i], values[i + 1]
        if a == 0 and b == 0:
            continue
        family = "PCBU"[(a & 0xC0) >> 6]
        first_digit = (a & 0x30) >> 4
        second_digit = a & 0x0F
        codes.append(f"{family}{first_digit}{second_digit:X}{b:02X}")
    return codes


def parse_dtc_response(response: str, mode_response: int) -> list[str]:
    data = _hex_bytes(response)
    marker = mode_response
    try:
        index = data.index(marker)
    except ValueError:
        return []
    return parse_dtc_bytes(data[index + 1 :])


def parse_supported_pids(response: str, base: int) -> set[int]:
    data = _hex_bytes(response)
    marker = [0x41, base]
    for i in range(len(data) - 5):
        if data[i : i + 2] == marker:
            mask = int.from_bytes(bytes(data[i + 2 : i + 6]), "big")
            return {base + bit + 1 for bit in range(32) if mask & (1 << (31 - bit))}
    return set()


def parse_vin(response: str) -> str:
    data = _hex_bytes(response)
    vin_bytes: list[int] = []
    i = 0
    while i < len(data) - 2:
        if data[i] == 0x49 and data[i + 1] == 0x02:
            i += 2
            if i < len(data) and data[i] <= 0x09:
                i += 1
            while i < len(data) and 0x20 <= data[i] <= 0x7E:
                vin_bytes.append(data[i])
                i += 1
        else:
            i += 1
    return bytes(vin_bytes[:17]).decode("ascii", errors="ignore")


def parse_pid_value(command: str, response: str) -> float | None:
    cmd = command.upper().replace(" ", "")
    definition = PID_DEFINITIONS.get(cmd)
    if not definition:
        return None
    pid = int(cmd[2:], 16)
    data = _hex_bytes(response)
    for i in range(len(data) - 2):
        if data[i] == 0x41 and data[i + 1] == pid:
            a = data[i + 2]
            b = data[i + 3] if i + 3 < len(data) else 0
            try:
                return float(definition[2](a, b))
            except Exception:
                return None
    return None


@dataclass
class DTCResult:
    code: str
    status: str


@dataclass
class VehicleScan:
    adapter: str = ""
    protocol_number: str = ""
    protocol_name: str = ""
    vin: str = ""
    supported_pids: set[int] = field(default_factory=set)
    monitor_raw: str = ""
    dtcs: list[DTCResult] = field(default_factory=list)


class ELM327Client:
    INIT_COMMANDS = ("ATZ", "ATE0", "ATL0", "ATS1", "ATH0", "ATCAF1", "ATCFC1", "ATAT2", "ATST64", "ATSP0")

    def __init__(self, transport: Transport, logger, console_callback: Callable[[str], None] | None = None):
        self.transport = transport
        self.logger = logger
        self.console_callback = console_callback
        self.lock = threading.RLock()
        self.connected = False
        self.adapter_name = ""
        self.protocol_number = ""
        self.protocol_name = ""
        self.supported_pids: set[int] = set()

    def _console(self, message: str) -> None:
        if self.console_callback:
            self.console_callback(message)

    def command(self, command: str, timeout: float = 3.0) -> str:
        with self.lock:
            self.logger.info("TX  %s", command)
            self._console(f"TX  {command}")
            raw = self.transport.query(command, timeout=timeout)
            response = _normalize_response(raw, command)
            self.logger.info("RX  %s", response)
            self._console(f"RX  {response}")
            return response

    def connect(self) -> None:
        self.transport.open()
        try:
            for command in self.INIT_COMMANDS:
                response = self.command(command, timeout=5.0 if command == "ATZ" else 3.0)
                if command == "ATZ":
                    self.adapter_name = response or "ELM327"
            probe = self.command("0100", timeout=8.0)
            if "NO DATA" in probe or not parse_supported_pids(probe, 0x00):
                raise OBDProtocolError("No se recibió respuesta OBD-II válida para PID 0100")
            self.protocol_number = self.command("ATDPN")
            self.protocol_name = self.command("ATDP")
            self.connected = True
        except Exception:
            self.transport.close()
            raise

    def close(self) -> None:
        self.connected = False
        self.transport.close()

    def detect_supported_pids(self) -> set[int]:
        supported: set[int] = set()
        for base in (0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0):
            response = self.command(f"01{base:02X}")
            block = parse_supported_pids(response, base)
            if not block:
                if base == 0:
                    raise OBDProtocolError("No fue posible leer la disponibilidad de PIDs")
                break
            supported.update(block)
            if base + 0x20 not in block:
                break
        self.supported_pids = supported
        return supported

    def read_vin(self) -> str:
        return parse_vin(self.command("0902", timeout=5.0))

    def read_dtcs(self) -> list[DTCResult]:
        result: list[DTCResult] = []
        modes = (("03", 0x43, "Confirmado / almacenado"), ("07", 0x47, "Pendiente"), ("0A", 0x4A, "Permanente"))
        for command, marker, status in modes:
            for code in parse_dtc_response(self.command(command), marker):
                result.append(DTCResult(code, status))
        return result

    def clear_dtcs(self) -> bool:
        response = self.command("04", timeout=5.0)
        return "44" in response or "OK" in response

    def read_monitor_status(self) -> dict[str, object]:
        response = self.command("0101")
        data = _hex_bytes(response)
        for i in range(len(data) - 5):
            if data[i : i + 2] == [0x41, 0x01]:
                a, b, c, d = data[i + 2 : i + 6]
                mil = bool(a & 0x80)
                count = a & 0x7F
                return {
                    "mil": mil,
                    "dtc_count": count,
                    "raw": f"{a:02X} {b:02X} {c:02X} {d:02X}",
                    "misfire_available": bool(b & 0x01),
                    "fuel_available": bool(b & 0x02),
                    "components_available": bool(b & 0x04),
                }
        return {"mil": False, "dtc_count": 0, "raw": response}

    def read_voltage(self) -> float | None:
        response = self.command("ATRV")
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*V", response)
        return float(match.group(1)) if match else None

    def read_live_pid(self, command: str) -> tuple[str, float | None, str]:
        response = self.command(command)
        name, unit, _ = PID_DEFINITIONS[command]
        return name, parse_pid_value(command, response), unit

    def read_live_data(self, commands: Iterable[str] | None = None) -> dict[str, tuple[float | None, str]]:
        result: dict[str, tuple[float | None, str]] = {}
        for command in commands or LIVE_PID_ORDER:
            pid = int(command[2:], 16)
            if self.supported_pids and pid not in self.supported_pids and command not in {"015E", "012F"}:
                continue
            name, value, unit = self.read_live_pid(command)
            result[name] = (value, unit)
        voltage = self.read_voltage()
        result["Voltaje adaptador"] = (voltage, "V")
        return result

    def read_freeze_frame(self) -> dict[str, tuple[float | str | None, str]]:
        result: dict[str, tuple[float | str | None, str]] = {}
        commands = {"DTC asociado": "020200", "RPM": "020C00", "Velocidad": "020D00", "Refrigerante": "020500", "Carga": "020400"}
        for label, command in commands.items():
            response = self.command(command)
            data = _hex_bytes(response)
            if label == "DTC asociado":
                try:
                    idx = data.index(0x42)
                    codes = parse_dtc_bytes(data[idx + 2 : idx + 4])
                    result[label] = (codes[0] if codes else "Sin dato", "")
                except Exception:
                    result[label] = ("Sin dato", "")
                continue
            mode1 = "01" + command[2:4]
            value = parse_pid_value(mode1, response.replace("42", "41", 1))
            unit = PID_DEFINITIONS.get(mode1, ("", "", None))[1]
            result[label] = (value, unit)
        return result

    def full_scan(self) -> VehicleScan:
        supported = self.detect_supported_pids()
        vin = self.read_vin()
        monitors = self.read_monitor_status()
        dtcs = self.read_dtcs()
        return VehicleScan(
            adapter=self.adapter_name,
            protocol_number=self.protocol_number,
            protocol_name=self.protocol_name,
            vin=vin,
            supported_pids=supported,
            monitor_raw=str(monitors.get("raw", "")),
            dtcs=dtcs,
        )


def create_client(
    mode: str,
    logger,
    console_callback: Callable[[str], None] | None = None,
    *,
    serial_port: str = "",
    baudrate: int = 38400,
    wifi_host: str = "192.168.0.10",
    wifi_port: int = 35000,
) -> ELM327Client:
    normalized = mode.strip().lower()
    if normalized == "simulador":
        transport: Transport = SimulatorTransport()
    elif normalized == "wifi":
        transport = WiFiTransport(wifi_host, wifi_port)
    elif normalized == "com":
        if not serial_port:
            raise OBDConnectionError("Seleccione un puerto COM")
        transport = SerialTransport(serial_port, baudrate)
    else:
        raise OBDConnectionError(f"Modo de conexión no válido: {mode}")
    return ELM327Client(transport, logger, console_callback)
