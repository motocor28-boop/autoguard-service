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


PID_DEFINITIONS = {
    0x05: ("Temperatura refrigerante", "°C"),
    0x0C: ("RPM", "rpm"),
    0x0D: ("Velocidad", "km/h"),
    0x10: ("Flujo de aire MAF", "g/s"),
    0x11: ("Posición acelerador", "%"),
    0x42: ("Voltaje módulo", "V"),
    0x5E: ("Flujo de combustible", "L/h"),
}


def parse_pid_value(pid: int, data: bytes) -> float:
    if pid == 0x05 and len(data) >= 1:
        return float(data[0] - 40)
    if pid == 0x0C and len(data) >= 2:
        return ((data[0] * 256) + data[1]) / 4.0
    if pid == 0x0D and len(data) >= 1:
        return float(data[0])
    if pid == 0x10 and len(data) >= 2:
        return ((data[0] * 256) + data[1]) / 100.0
    if pid == 0x11 and len(data) >= 1:
        return data[0] * 100.0 / 255.0
    if pid == 0x42 and len(data) >= 2:
        return ((data[0] * 256) + data[1]) / 1000.0
    if pid == 0x5E and len(data) >= 2:
        return ((data[0] * 256) + data[1]) / 20.0
    raise ValueError(f"PID 0x{pid:02X} sin fórmula o respuesta incompleta")


def estimate_fuel_rate_from_maf(maf_g_s: float, fuel_density_kg_l: float = 0.745, afr: float = 14.7) -> float:
    """Estima L/h desde MAF para gasolina estequiométrica.

    La aplicación siempre marca este valor como estimado. No reemplaza una lectura
    directa del PID 015E ni una medición física de combustible.
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
        rpm = 820.0 + 500.0 * max(0.0, math.sin(t / 3.0)) + random.uniform(-12, 12)
        speed = max(0.0, 42.0 + 20.0 * math.sin(t / 8.0))
        coolant = min(96.0, 72.0 + t / 40.0)
        voltage = 13.85 + random.uniform(-0.08, 0.08)
        throttle = max(2.0, min(75.0, 18.0 + 15.0 * math.sin(t / 4.0)))
        maf = max(2.0, rpm * (0.0035 + throttle / 10000.0))
        fuel = estimate_fuel_rate_from_maf(maf)
        return {
            0x05: coolant,
            0x0C: rpm,
            0x0D: speed,
            0x10: maf,
            0x11: throttle,
            0x42: voltage,
            0x5E: fuel,
        }

    def _sim_command(self, command: str) -> str:
        if command == "ATDP":
            return "AUTO, ISO 15765-4 (CAN 11/500)>"
        if command.startswith("AT"):
            return "OK>"
        if command in {"0100", "0120", "0140", "0160"}:
            return "41" + command[2:] + "FFFFFFFF>"
        if command.startswith("01") and len(command) >= 4:
            pid = int(command[2:4], 16)
            value = self._sim_values().get(pid, 0.0)
            if pid == 0x05:
                raw = bytes([max(0, min(255, round(value + 40)))])
            elif pid == 0x0C:
                integer = max(0, min(65535, round(value * 4)))
                raw = integer.to_bytes(2, "big")
            elif pid == 0x0D:
                raw = bytes([max(0, min(255, round(value)))])
            elif pid == 0x10:
                raw = max(0, min(65535, round(value * 100))).to_bytes(2, "big")
            elif pid == 0x11:
                raw = bytes([max(0, min(255, round(value * 255 / 100)))])
            elif pid == 0x42:
                raw = max(0, min(65535, round(value * 1000))).to_bytes(2, "big")
            elif pid == 0x5E:
                raw = max(0, min(65535, round(value * 20))).to_bytes(2, "big")
            else:
                raw = b"\x00\x00"
            return f"41{pid:02X}{raw.hex().upper()}>"
        if command in {"03", "07", "0A"}:
            return "43 01 33 03 00 04 20 00 00>"
        if command == "04":
            return "44>"
        return "NO DATA>"

    def query_pid(self, pid: int) -> float:
        response = self.command(f"01{pid:02X}")
        data = _extract_mode01_bytes(response, pid)
        return parse_pid_value(pid, data)

    def supported_pids(self) -> set[int]:
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
