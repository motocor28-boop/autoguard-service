from __future__ import annotations

from deep_scan import discover_headers, parse_readiness
from diagnostic_parsers import parse_uds_ascii, parse_uds_dtcs


def test_parse_readiness_status() -> None:
    result = parse_readiness("41 01 82 07 E8 00 >")
    assert result["available"] is True
    assert result["mil_encendida"] is True
    assert result["cantidad_dtc_confirmados"] == 2
    assert result["tipo_encendido"] == "Chispa"


def test_discover_standard_can_headers() -> None:
    response = "7E8 06 41 00 BE 3F A8 13\r7E9 06 41 00 80 00 00 01\r>"
    modules = discover_headers(response)
    assert ("7E8", "7E0", "Motor / PCM") in modules
    assert any(item[0] == "7E9" and item[1] == "7E1" for item in modules)


def test_discover_29bit_header() -> None:
    response = "18DAF110 06 41 00 BE 3F A8 13\r>"
    modules = discover_headers(response)
    assert modules[0][0] == "18DAF110"
    assert modules[0][1] == "18DA10F1"


def test_parse_uds_identification_multiframe() -> None:
    response = (
        "7E8 10 14 62 F1 90 56 46\r"
        "7E8 21 31 41 42 43 44 45 46\r"
        "7E8 22 47 48 31 32 33 34 35\r"
        "7E8 23 36 37 38 39 30 00 00\r>"
    )
    value = parse_uds_ascii(response, "F190")
    assert value.startswith("VF1ABCDEFGH1234567890"[:17])


def test_parse_uds_dtc_records() -> None:
    response = "59 02 FF 01 23 45 08 A1 B2 C3 01 >"
    codes = parse_uds_dtcs(response)
    assert "012345 · estado 0x08" in codes
    assert "A1B2C3 · estado 0x01" in codes
