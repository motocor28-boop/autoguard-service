from __future__ import annotations

from pathlib import Path

import pytest

from core import decode_dtc_payload, estimate_fuel_rate_from_maf, parse_pid_value
from dtc_database import DtcDatabase


def test_pid_formulas() -> None:
    assert parse_pid_value(0x05, bytes([120])) == 80
    assert parse_pid_value(0x0C, bytes([0x1A, 0xF8])) == 1726
    assert parse_pid_value(0x0D, bytes([88])) == 88
    assert parse_pid_value(0x10, bytes([0x01, 0xF4])) == 5.0
    assert parse_pid_value(0x11, bytes([255])) == 100.0
    assert parse_pid_value(0x42, bytes([0x36, 0xB0])) == pytest.approx(14.0)
    assert parse_pid_value(0x5E, bytes([0x00, 0x64])) == 5.0


def test_fuel_flow_maf_fallback() -> None:
    value = estimate_fuel_rate_from_maf(14.7, fuel_density_kg_l=0.735, afr=14.7)
    assert value == pytest.approx(4.897959, rel=1e-5)
    with pytest.raises(ValueError):
        estimate_fuel_rate_from_maf(-1)


def test_dtc_decoder() -> None:
    assert decode_dtc_payload("01 33 03 00 04 20") == ["P0133", "P0300", "P0420"]


def test_expanded_database() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "autoguard_dtc.sqlite"
    database = DtcDatabase(path)
    stats = database.stats()
    assert stats["unique_codes"] >= 10_000
    assert stats["definitions"] >= stats["unique_codes"]
    records = database.lookup("U0123")
    assert records
    assert "guiñada" in records[0].description.lower()
