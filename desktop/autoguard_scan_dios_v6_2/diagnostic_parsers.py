from __future__ import annotations

import re


def _hex_tokens(line: str) -> list[int]:
    tokens = re.findall(r"(?<![0-9A-Fa-f])([0-9A-Fa-f]{2})(?![0-9A-Fa-f])", line)
    return [int(token, 16) for token in tokens]


def diagnostic_payload(text: str) -> bytes:
    """Reconstruct diagnostic payload from ELM327 text, CAN headers and ISO-TP.

    Supports common 11-bit and 29-bit header output with spaced bytes. If the
    adapter returns a compact unheaded response, falls back to compact parsing.
    """
    payload = bytearray()
    parsed_line = False
    for raw_line in text.replace(">", "\n").splitlines():
        line = raw_line.strip().upper()
        if not line or "NO DATA" in line or line.startswith("SEARCHING"):
            continue
        parts = line.split()
        if not parts:
            continue
        header_present = bool(re.fullmatch(r"[0-9A-F]{3}|[0-9A-F]{8}", parts[0]))
        if header_present:
            parts = parts[1:]
        byte_values: list[int] = []
        for part in parts:
            if re.fullmatch(r"[0-9A-F]{2}", part):
                byte_values.append(int(part, 16))
        if not byte_values:
            continue
        parsed_line = True
        pci = byte_values[0]
        frame_type = pci >> 4
        if frame_type == 0x0 and len(byte_values) >= 2:
            length = pci & 0x0F
            payload.extend(byte_values[1:1 + length] if length else byte_values[1:])
        elif frame_type == 0x1 and len(byte_values) >= 3:
            total_length = ((pci & 0x0F) << 8) | byte_values[1]
            payload.extend(byte_values[2:])
            if total_length and len(payload) > total_length:
                del payload[total_length:]
        elif frame_type == 0x2 and len(byte_values) >= 2:
            payload.extend(byte_values[1:])
        elif frame_type == 0x3:
            continue
        else:
            payload.extend(byte_values)

    if parsed_line and payload:
        return bytes(payload)

    compact = re.sub(r"[^0-9A-Fa-f]", "", text)
    if len(compact) % 2:
        compact = compact[:-1]
    try:
        return bytes.fromhex(compact)
    except ValueError:
        return b""


def extract_after_marker(text: str, marker: str) -> bytes:
    stream = diagnostic_payload(text)
    try:
        marker_bytes = bytes.fromhex(marker)
    except ValueError:
        return b""
    index = stream.find(marker_bytes)
    if index >= 0:
        return stream[index + len(marker_bytes):]

    # Fallback for mixed adapter text where payload reconstruction is partial.
    compact = re.sub(r"[^0-9A-F]", "", text.upper())
    marker_hex = marker.upper()
    position = compact.find(marker_hex)
    if position < 0:
        return b""
    remaining = compact[position + len(marker_hex):]
    if len(remaining) % 2:
        remaining = remaining[:-1]
    try:
        return bytes.fromhex(remaining)
    except ValueError:
        return b""


def decode_printable(data: bytes) -> str:
    return "".join(chr(value) for value in data if 32 <= value <= 126).strip(" \x00")


def parse_uds_ascii(text: str, did: str) -> str:
    return decode_printable(extract_after_marker(text, f"62{did}"))


def parse_uds_dtcs(text: str) -> list[str]:
    data = extract_after_marker(text, "5902")
    if len(data) < 2:
        return []
    payload = data[1:]
    results: list[str] = []
    for index in range(0, len(payload) - 3, 4):
        dtc = payload[index:index + 3].hex().upper()
        status = payload[index + 3]
        if dtc != "000000":
            results.append(f"{dtc} · estado 0x{status:02X}")
    return results
