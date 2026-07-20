from __future__ import annotations

from deep_scan import (
    DeepScanResult,
    DeepScanner,
    FUEL_TYPE,
    OBD_STANDARD,
    _decode_printable,
    _extract_after_marker,
    _mode01_bytes,
    _mode02_bytes,
)
from core import PID_DEFINITIONS, parse_pid_value


class DeepScannerFull(DeepScanner):
    """Maximum read-only coverage available through the connected ELM327.

    Every PID announced by the ECU is queried and preserved as a raw response.
    Values with a standardized formula are additionally decoded. Mode 09
    information PIDs are discovered dynamically and queried as raw data.
    """

    def _standard_values(self, result: DeepScanResult) -> None:
        for pid in result.supported_pids:
            response = self._command(result, f"PID_RAW_{pid:02X}", f"01{pid:02X}")
            data = _mode01_bytes(response, pid)
            if pid not in PID_DEFINITIONS:
                continue
            try:
                value = parse_pid_value(pid, data)
            except Exception:
                continue
            name, unit = PID_DEFINITIONS[pid]
            result.live_values[f"01{pid:02X}"] = {
                "name": name,
                "value": value,
                "unit": unit,
                "raw": data.hex(" ").upper(),
            }

        obd_response = self._command(result, "OBD_STANDARD", "011C")
        obd_data = _mode01_bytes(obd_response, 0x1C)
        if obd_data:
            result.vehicle_information["Norma OBD"] = OBD_STANDARD.get(
                obd_data[0], f"Valor 0x{obd_data[0]:02X}"
            )
        fuel_response = self._command(result, "FUEL_TYPE", "0151")
        fuel_data = _mode01_bytes(fuel_response, 0x51)
        if fuel_data:
            result.vehicle_information["Tipo de combustible ECU"] = FUEL_TYPE.get(
                fuel_data[0], f"Valor 0x{fuel_data[0]:02X}"
            )

    def _supported_mode09(self, result: DeepScanResult) -> list[int]:
        supported: set[int] = set()
        for base in range(0x00, 0x100, 0x20):
            response = self._command(result, f"MODE09_BLOCK_{base:02X}", f"09{base:02X}", timeout=5.0)
            data = _extract_after_marker(response, f"49{base:02X}")
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
        info_pids = self._supported_mode09(result)
        result.vehicle_information["Mode 09 PID publicados"] = ", ".join(
            f"09{pid:02X}" for pid in info_pids
        ) or "No publicados"
        responses: dict[int, str] = {}
        for pid in info_pids:
            responses[pid] = self._command(
                result,
                f"MODE09_RAW_{pid:02X}",
                f"09{pid:02X}",
                timeout=6.0,
            )

        # Query the principal standardized information PIDs even if the support
        # mask is absent or malformed, because some ECUs still answer them.
        for pid in (0x02, 0x04, 0x06, 0x08, 0x0A):
            responses.setdefault(
                pid,
                self._command(result, f"MODE09_DIRECT_{pid:02X}", f"09{pid:02X}", timeout=6.0),
            )

        mapping = {
            0x02: ("VIN", True),
            0x04: ("ID de calibración", True),
            0x06: ("CVN", False),
            0x08: ("Contadores de desempeño en uso", False),
            0x0A: ("Nombre ECU", True),
        }
        for pid, (label, ascii_value) in mapping.items():
            response = responses.get(pid, "")
            data = _extract_after_marker(response, f"49{pid:02X}")
            if not data:
                continue
            value = _decode_printable(data) if ascii_value else data.hex(" ").upper()
            if value:
                result.vehicle_information[label] = value

    def _freeze_frame(self, result: DeepScanResult) -> None:
        # Mode 02 responses are preserved for every PID announced by Mode 01.
        # ECUs without a stored freeze frame normally answer NO DATA.
        for pid in result.supported_pids:
            response = self._command(result, f"FREEZE_RAW_{pid:02X}", f"02{pid:02X}")
            data = _mode02_bytes(response, pid)
            if pid not in PID_DEFINITIONS:
                continue
            try:
                value = parse_pid_value(pid, data)
            except Exception:
                continue
            name, unit = PID_DEFINITIONS[pid]
            result.freeze_frame[f"02{pid:02X}"] = {
                "name": name,
                "value": value,
                "unit": unit,
                "raw": data.hex(" ").upper(),
            }

    def _mode06(self, result: DeepScanResult) -> None:
        # Mode 05 is retained for older/non-CAN oxygen-sensor test data.
        self._command(result, "MODE05_OXYGEN_TESTS", "05", timeout=8.0)
        super()._mode06(result)
