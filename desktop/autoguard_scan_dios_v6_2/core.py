from __future__ import annotations

import math
import queue
import random
import re
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterable


class OBDConnectionError(RuntimeError):
    pass


# Standard Mode 01 PIDs with formulas implemented below. The application only
# polls PIDs announced by the ECU, except in simulator mode.
PID_DEFINITIONS: dict[int, tuple[str, str]] = {
    0x04: ("Carga calculada del motor", "%"),
    0x05: ("Temperatura refrigerante", "°C"),
    0x06: ("Corrección corta combustible B1", "%"),
    0x07: ("Corrección larga combustible B1", "%"),
    0x08: ("Corrección corta combustible B2", "%"),
    0x09: ("Corrección larga combustible B2", "%"),
    0x0A: ("Presión de combustible", "kPa"),
    0x0B: ("Presión absoluta MAP", "kPa"),
    0x0C: ("RPM del motor", "rpm"),
    0x0D: ("Velocidad del vehículo", "km/h"),
    0x0E: ("Avance de encendido", "°"),
    0x0F: ("Temperatura aire admisión", "°C"),
    0x10: ("Flujo de aire MAF", "g/s"),
    0x11: ("Posición del acelerador", "%"),
    0x1F: ("Tiempo desde arranque", "s"),
    0x21: ("Distancia con MIL encendida", "km"),
    0x22: ("Presión riel relativa", "kPa"),
    0x23: ("Presión riel directa", "kPa"),
    0x2C: ("EGR comandada", "%"),
    0x2D: ("Error EGR", "%"),
    0x2E: ("Purga EVAP comandada", "%"),
    0x2F: ("Nivel de combustible", "%"),
    0x30: ("Arranques desde borrado DTC", "ciclos"),
    0x31: ("Distancia desde borrado DTC", "km"),
    0x33: ("Presión barométrica", "kPa"),
    0x3C: ("Temperatura catalizador B1S1", "°C"),
    0x3D: ("Temperatura catalizador B2S1", "°C"),
    0x3E: ("Temperatura catalizador B1S2", "°C"),
    0x3F: ("Temperatura catalizador B2S2", "°C"),
    0x42: ("Voltaje módulo de control", "V"),
    0x45: ("Posición relativa acelerador", "%"),
    0x46: ("Temperatura ambiente", "°C"),
    0x47: ("Acelerador absoluto B", "%"),
    0x49: ("Pedal acelerador D", "%"),
    0x4A: ("Pedal acelerador E", "%"),
    0x4B: ("Pedal acelerador F", "%"),
    0x4C: ("Actuador acelerador comandado", "%"),
    0x4D: ("Tiempo con MIL encendida", "min"),
    0x4E: ("Tiempo desde borrado DTC", "min"),
    0x52: ("Porcentaje de etanol", "%"),
    0x5A: ("Pedal acelerador relativo", "%"),
    0x5B: ("Vida restante batería híbrida", "%"),
    0x5C: ("Temperatura aceite motor", "°C"),
    0x5D: ("Tiempo de inyección", "°"),
    0x5E: ("Flujo de combustible", "L/h"),
    0x61: ("Demanda de torque conductor", "%"),
    0x62: ("Torque real del motor", "%"),
    0x63: ("Torque de referencia", "Nm"),
}


PID_RANGES: dict[int, tuple[float, float]] = {
    0x04: (0, 100), 0x05: (-40, 130), 0x06: (-100, 99), 0x07: (-100, 99),
    0x08: (-100, 99), 0x09: (-100, 99), 0x0A: (0, 765), 0x0B: (0, 255),
    0x0C: (0, 8000), 0x0D: (0, 255), 0x0E: (-64, 64), 0x0F: (-40, 130),
    0x10: (0, 655), 0x11: (0, 100), 0x1F: (0, 65535), 0x21: (0, 65535),
    0x22: (0, 5177), 0x23: (0, 655350), 0x2C: (0, 100), 0x2D: (-100, 99),
    0x2E: (0, 100), 0x2F: (0, 100), 0x30: (0, 255), 0x31: (0, 65535),
    0x33: (0, 255), 0x3C: (-40, 6513), 0x3D: (-40, 6513), 0x3E: (-40, 6513),
    0x3F: (-40, 6513), 0x42: (0, 65.5), 0x45: (0, 100), 0x46: (-40, 130),
    0x47: (0, 100), 0x49: (0, 100), 0x4A: (0, 100), 0x4B: (0, 100),
    0x4C: (0, 100), 0x4D: (0, 65535), 0x4E: (0, 65535), 0x52: (0, 100),
    0x5A: (0, 100), 0x5B: (0, 100), 0x5C: (-40, 210), 0x5D: (-210, 301),
    0x5E: (0, 3212), 0x61: (-125, 125), 0x62: (-125, 125), 0x63: (0, 65535),
}


def _u16(data: bytes) -> int:
    if len(data) < 2:
        raise ValueError("Respuesta incompleta: se requieren dos bytes")
    return data[0] * 256 + data[1]


def _percent(byte: int) -> float:
    return byte * 100.0 / 255.0


def _signed_percent(byte: int) -> float:
    return byte * 100.0 / 128.0 - 100.0


def parse_pid_value(pid: int, data: bytes) -> float:
    if not data:
        raise ValueError(f"PID 0x{pid:02X} sin datos")
    a = data[0]
    if pid == 0x04:
        return _percent(a)
    if pid == 0x05:
        return float(a - 40)
    if pid in {0x06, 0x07, 0x08, 0x09, 0x2D}:
        return _signed_percent(a)
    if pid == 0x0A:
        return float(a * 3)
    if pid in {0x0B, 0x0D, 0x30, 0x33}:
        return float(a)
    if pid == 0x0C:
        return _u16(data) / 4.0
    if pid == 0x0E:
        return a / 2.0 - 64.0
    if pid in {0x0F, 0x46, 0x5C}:
        return float(a - 40)
    if pid == 0x10:
        return _u16(data) / 100.0
    if pid in {0x11, 0x2C, 0x2E, 0x2F, 0x45, 0x47, 0x49, 0x4A, 0x4B, 0x4C, 0x52, 0x5A, 0x5B}:
        return _percent(a)
    if pid in {0x1F, 0x21, 0x31, 0x4D, 0x4E, 0x63}:
        return float(_u16(data))
    if pid == 0x22:
        return _u16(data) * 0.079
    if pid == 0x23:
        return float(_u16(data) * 10)
    if pid in {0x3C, 0x3D, 0x3E, 0x3F}:
        return _u16(data) / 10.0 - 40.0
    if pid == 0x42:
        return _u16(data) / 1000.0
    if pid == 0x5D:
        return _u16(data) / 128.0 - 210.0
    if pid == 0x5E:
        return _u16(data) / 20.0
    if pid in {0x61, 0x62}:
        return float(a - 125)
    raise ValueError(f"PID 0x{pid:02X} sin fórmula implementada")


def estimate_fuel_rate_from_maf(maf_g_s: float, fuel_density_kg_l: float = 0.745, afr: float = 14.7) -> float:
    """Estima L/h desde MAF para gasolina estequiométrica.

    El valor siempre debe mostrarse como estimado. No reemplaza una lectura
    directa del PID 015E ni una medición física del circuito de combustible.
    """
    if maf_g_s < 0:
        raise ValueError("MAF no puede ser negativo")
    if fuel_density_kg_l <= 0 or afr <= 0:
        raise ValueError("Densidad y AFR deben ser positivos")
    fuel_g_s = maf_g_s / afr
    return (fuel_g_s * 3600.0) / (fuel_density_kg_l * 1000.0)


def decode_dtc_word(value: int) -> str:
    system = "PCBU"[(value >> 14) & 0x03]
    digit1 = (value >> 12) & 0x03
    digit2 = (value >> 8) & 0x0F
    digit3 = (value >> 4) & 0x0F
    digit4 = value & 0x0F
    return f"{system}{digit1:X}{digit2:X}{digit3:X}{digit4:X}"


def decode_dtc_payload(hex_payload: str) -> list[str]:
    clean = re.sub(r"[^0-9A-Fa-f]", "", hex_payload).upper()
    codes: list[str] = []
    for i in range(0, len(clean) - 3, 4):
        word = int(clean[i : i + 4], 16)
        if word == 0:
            continue
        code = decode_dtc_word(word)
        if code not in codes:
            codes.append(code)
    return codes


def _extract_mode01_bytes(response: str, pid: int) -> bytes:
    normalized = response.upper().replace("SEARCHING...", " ")
    tokens = re.findall(r"\b[0-9A-F]{2}\b", normalized)
    target = ["41", f"{pid:02X}"]
    for index in range(len(tokens) - 1):
        if tokens[index : index + 2] == target:
            return bytes(int(value, 16) for value in tokens[index + 2 :])
    compact = re.sub(r"[^0-9A-F]", "", normalized)
    marker = f"41{pid:02X}"
    position = compact.find(marker)
    if position >= 0:
        payload = compact[position + len(marker) :]
        if len(payload) % 2:
            payload = payload[:-1]
        return bytes.fromhex(payload)
    raise ValueError(f"Respuesta inválida para PID {pid:02X}: {response!r}")


@dataclass(slots=True)
class ConnectionConfig:
    mode: str = "Simulador"
    serial_port: str = "COM3"
    baudrate: int = 38400
    wifi_host: str = "192.168.0.10"
    wifi_port: int = 35000
    timeout: float = 2.0


class ELM327Client:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.log = log or (lambda _message: None)
        self._serial = None
        self._socket: socket.socket | None = None
        self._mode = ""
        self._lock = threading.RLock()
        self.connected = False
        self.protocol = "Sin conexión"
        self._sim_start = time.monotonic()

    @staticmethod
    def available_serial_ports() -> list[str]:
        try:
            from serial.tools import list_ports
            return [port.device for port in list_ports.comports()]
        except Exception:
            return []

    def connect(self, config: ConnectionConfig) -> str:
        self.disconnect()
        self._mode = config.mode.lower()
        self.log(f"Conectando mediante {config.mode}...")
        if self._mode.startswith("sim"):
            self.connected = True
            self.protocol = "SIMULADOR OBD-II CAN"
            self._sim_start = time.monotonic()
            self.log("Simulador conectado")
            return self.protocol
        if self._mode.startswith("com"):
            try:
                import serial
                self._serial = serial.Serial(
                    port=config.serial_port,
                    baudrate=config.baudrate,
                    timeout=config.timeout,
                    write_timeout=config.timeout,
                )
            except Exception as exc:
                raise OBDConnectionError(f"No fue posible abrir {config.serial_port}: {exc}") from exc
        elif self._mode.startswith("wifi") or self._mode.startswith("wi-fi"):
            try:
                self._socket = socket.create_connection(
                    (config.wifi_host, config.wifi_port), timeout=config.timeout
                )
                self._socket.settimeout(config.timeout)
            except OSError as exc:
                raise OBDConnectionError(
                    f"No fue posible conectar a {config.wifi_host}:{config.wifi_port}: {exc}"
                ) from exc
        else:
            raise OBDConnectionError(f"Modo no reconocido: {config.mode}")

        self.connected = True
        try:
            for command in ("ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP0"):
                self.command(command, timeout=max(config.timeout, 3.0))
            protocol = self.command("ATDP")
            self.protocol = protocol.replace(">", "").strip() or "AUTO"
            self.log(f"Protocolo: {self.protocol}")
            return self.protocol
        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        with self._lock:
            try:
                if self._serial is not None:
                    self._serial.close()
            finally:
                self._serial = None
            try:
                if self._socket is not None:
                    self._socket.close()
            finally:
                self._socket = None
            self.connected = False
            self.protocol = "Sin conexión"

    def _read_until_prompt(self, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        chunks: list[bytes] = []
        while time.monotonic() < deadline:
            if self._serial is not None:
                waiting = max(getattr(self._serial, "in_waiting", 0), 1)
                chunk = self._serial.read(waiting)
            elif self._socket is not None:
                try:
                    chunk = self._socket.recv(4096)
                except socket.timeout:
                    chunk = b""
            else:
                raise OBDConnectionError("Transporte no disponible")
            if chunk:
                chunks.append(chunk)
                if b">" in chunk:
                    break
            else:
                time.sleep(0.02)
        text = b"".join(chunks).decode("ascii", errors="replace")
        if not text.strip():
            raise TimeoutError("ELM327 no respondió dentro del tiempo configurado")
        return text

    def command(self, command: str, timeout: float = 2.5) -> str:
        if not self.connected:
            raise OBDConnectionError("No existe conexión activa")
        command = command.strip().upper()
        if self._mode.startswith("sim"):
            return self._sim_command(command)
        payload = (command + "\r").encode("ascii")
        with self._lock:
            self.log(f"> {command}")
            if self._serial is not None:
                self._serial.reset_input_buffer()
                self._serial.write(payload)
                self._serial.flush()
            elif self._socket is not None:
                self._socket.sendall(payload)
            response = self._read_until_prompt(timeout)
            self.log(response.replace("\r", " ").replace("\n", " ").strip())
            return response

    def _sim_values(self) -> dict[int, float]:
        t = time.monotonic() - self._sim_start
        rpm = 820.0 + 1350.0 * max(0.0, math.sin(t / 3.0)) + random.uniform(-12, 12)
        speed = max(0.0, 48.0 + 24.0 * math.sin(t / 8.0))
        coolant = min(96.0, 72.0 + t / 40.0)
        voltage = 13.85 + random.uniform(-0.08, 0.08)
        throttle = max(2.0, min(75.0, 18.0 + 15.0 * math.sin(t / 4.0)))
        maf = max(2.0, rpm * (0.0035 + throttle / 10000.0))
        fuel = estimate_fuel_rate_from_maf(maf)
        load = min(100.0, 15.0 + throttle * 0.8)
        return {
            0x04: load, 0x05: coolant, 0x06: 2.2, 0x07: -1.4, 0x08: 1.5, 0x09: -0.8,
            0x0A: 330.0, 0x0B: 34.0 + throttle * 0.3, 0x0C: rpm, 0x0D: speed,
            0x0E: 14.0 + math.sin(t / 2.0) * 4.0, 0x0F: 31.0, 0x10: maf, 0x11: throttle,
            0x1F: t, 0x21: 0.0, 0x22: 380.0, 0x23: 4200.0, 0x2C: 8.0,
            0x2D: 0.8, 0x2E: 12.0, 0x2F: max(0.0, 67.0 - t / 3600.0), 0x30: 14.0,
            0x31: 182.0, 0x33: 96.0, 0x3C: 480.0, 0x3D: 470.0, 0x3E: 390.0,
            0x3F: 385.0, 0x42: voltage, 0x45: throttle, 0x46: 24.0, 0x47: throttle,
            0x49: throttle, 0x4A: throttle, 0x4B: throttle, 0x4C: throttle, 0x4D: 0.0,
            0x4E: 420.0, 0x52: 8.0, 0x5A: throttle, 0x5B: 82.0, 0x5C: 91.0,
            0x5D: 6.0, 0x5E: fuel, 0x61: load - 20.0, 0x62: load - 18.0, 0x63: 240.0,
        }

    def _sim_command(self, command: str) -> str:
        if command == "ATDP":
            return "AUTO, ISO 15765-4 (CAN 11/500)>"
        if command.startswith("AT"):
            return "OK>"
        if command in {"0100", "0120", "0140", "0160"}:
            return "41" + command[2:] + "FFFFFFFF>"
        if command in {"03", "07", "0A"}:
            return "43 01 71 03 00 04 20 00 00>"
        if command == "04":
            return "44>"
        return "NO DATA>"

    def query_pid(self, pid: int) -> float:
        if self._mode.startswith("sim"):
            values = self._sim_values()
            if pid not in values:
                raise ValueError(f"PID {pid:02X} no disponible en simulador")
            return values[pid]
        response = self.command(f"01{pid:02X}")
        data = _extract_mode01_bytes(response, pid)
        return parse_pid_value(pid, data)

    def supported_pids(self) -> set[int]:
        if self._mode.startswith("sim"):
            return set(PID_DEFINITIONS)
        supported: set[int] = set()
        for base in (0x00, 0x20, 0x40, 0x60):
            try:
                response = self.command(f"01{base:02X}")
                data = _extract_mode01_bytes(response, base)
                if len(data) < 4:
                    continue
                mask = int.from_bytes(data[:4], "big")
                for bit in range(32):
                    if mask & (1 << (31 - bit)):
                        supported.add(base + bit + 1)
            except Exception as exc:
                self.log(f"No se pudo leer bloque PID {base:02X}: {exc}")
        return supported

    def read_dtcs(self, mode: str = "03") -> list[str]:
        response = self.command(mode)
        clean = re.sub(r"[^0-9A-Fa-f]", "", response).upper()
        expected = {"03": "43", "07": "47", "0A": "4A"}.get(mode, "43")
        marker = clean.find(expected)
        if marker >= 0:
            clean = clean[marker + 2 :]
        return decode_dtc_payload(clean)

    def clear_dtcs(self) -> bool:
        response = self.command("04")
        return "44" in response.replace(" ", "").upper()


class LiveDataWorker(threading.Thread):
    def __init__(
        self,
        client: ELM327Client,
        pids: Iterable[int],
        output: "queue.Queue[dict]",
        interval: float = 0.18,
    ) -> None:
        super().__init__(daemon=True)
        self.client = client
        self.pids = list(pids)
        self.output = output
        self.interval = max(0.08, interval)
        self.stop_event = threading.Event()

    def run(self) -> None:
        while not self.stop_event.is_set() and self.client.connected:
            values: dict[int, float] = {}
            errors: list[str] = []
            cycle_start = time.monotonic()
            for pid in self.pids:
                if self.stop_event.is_set():
                    break
                try:
                    values[pid] = self.client.query_pid(pid)
                except Exception as exc:
                    errors.append(f"PID {pid:02X}: {exc}")
            if 0x5E not in values and 0x10 in values:
                values[0x5E] = estimate_fuel_rate_from_maf(values[0x10])
                fuel_source = "Estimado desde MAF"
            elif 0x5E in values:
                fuel_source = "PID 015E · lectura directa ECU"
            else:
                fuel_source = "No disponible"
            self.output.put(
                {
                    "timestamp": time.time(),
                    "values": values,
                    "errors": errors,
                    "fuel_source": fuel_source,
                }
            )
            elapsed = time.monotonic() - cycle_start
            self.stop_event.wait(max(0.01, self.interval - elapsed))

    def stop(self) -> None:
        self.stop_event.set()
