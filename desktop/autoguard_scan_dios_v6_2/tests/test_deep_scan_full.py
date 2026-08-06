from __future__ import annotations

from deep_scan import DeepScanResult
from deep_scan_full import DeepScannerFull


class FakeClient:
    connected = True
    protocol = "ISO 15765-4 CAN"
    _mode = "simulador"

    def supported_pids(self):
        return {0x0C, 0x0D}

    def command(self, command: str, timeout: float = 3.0) -> str:
        responses = {
            "010C": "41 0C 1A F8 >",
            "010D": "41 0D 58 >",
            "011C": "41 1C 06 >",
            "0151": "41 51 01 >",
        }
        return responses.get(command, "NO DATA>")

    def query_pid(self, pid: int) -> float:
        return {0x0C: 1726.0, 0x0D: 88.0}[pid]


def test_full_scanner_reads_all_simulator_pids() -> None:
    scanner = DeepScannerFull(FakeClient())  # type: ignore[arg-type]
    result = DeepScanResult(started_at=0.0, supported_pids=[0x0C, 0x0D])
    scanner._standard_values(result)
    assert result.live_values["010C"]["value"] == 1726.0
    assert result.live_values["010D"]["value"] == 88.0
    assert "PID_RAW_0C" in result.raw_responses
    assert result.vehicle_information["Norma OBD"] == "EOBD"
    assert result.vehicle_information["Tipo de combustible ECU"] == "Gasolina"
