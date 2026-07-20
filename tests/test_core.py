from __future__ import annotations

import logging

from superscan.dtc_database import DTCDatabase, TOTAL_DTC_RECORDS
from superscan.obd import (
    SimulatorTransport,
    ELM327Client,
    parse_dtc_bytes,
    parse_dtc_response,
    parse_pid_value,
    parse_supported_pids,
    parse_vin,
)


def quiet_logger() -> logging.Logger:
    logger = logging.getLogger("superscan-tests")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    return logger


def test_dtc_catalog_has_exact_record_count(tmp_path):
    db = DTCDatabase(tmp_path / "dtc.sqlite3")
    assert db.count() == TOTAL_DTC_RECORDS == 12_133
    assert db.lookup("P0133").code == "P0133"
    assert "respuesta lenta" in db.lookup("P0133").description.lower()
    assert "comunicación perdida" in db.lookup("U0123").description.lower()


def test_dtc_parsing():
    assert parse_dtc_bytes([0x01, 0x33, 0x03, 0x00, 0x04, 0x20]) == ["P0133", "P0300", "P0420"]
    assert parse_dtc_response("43 01 33 03 00 04 20 00 00", 0x43) == ["P0133", "P0300", "P0420"]


def test_supported_pid_blocks_and_vin():
    pids = parse_supported_pids("41 00 BE 3E B8 13", 0x00)
    assert 0x0C in pids
    assert 0x0D in pids
    assert 0x20 in pids
    vin = parse_vin("49 02 01 4B 4C 31 4A 45 42 41 42 30 46 42 30 30 30 30 30 31")
    assert vin == "KL1JEBAB0FB000001"


def test_fuel_pid_formulas():
    assert parse_pid_value("015E", "41 5E 00 51") == 4.05
    level = parse_pid_value("012F", "41 2F 9F")
    assert level is not None
    assert round(level, 2) == 62.35


def test_simulator_full_session():
    client = ELM327Client(SimulatorTransport(), quiet_logger())
    client.connect()
    scan = client.full_scan()
    assert scan.vin == "KL1JEBAB0FB000001"
    assert "ISO 15765-4 CAN" in scan.protocol_name
    assert {"P0133", "P0300", "P0420", "P0171"}.issubset({item.code for item in scan.dtcs})
    live = client.read_live_data(["010C", "010D", "015E", "012F"])
    assert live["RPM motor"][0] is not None
    assert live["Caudal de combustible"][0] is not None
    assert live["Nivel de combustible"][0] is not None
    assert client.clear_dtcs()
    assert client.read_dtcs() == []
    client.close()
