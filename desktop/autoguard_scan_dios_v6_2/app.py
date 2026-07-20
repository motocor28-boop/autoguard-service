import deep_scan
from diagnostic_parsers import decode_printable, extract_after_marker, parse_uds_ascii, parse_uds_dtcs

# Install the ISO-TP aware parsers before the deep-scan modules are imported.
deep_scan._extract_after_marker = extract_after_marker
deep_scan._decode_printable = decode_printable
deep_scan.parse_uds_ascii = parse_uds_ascii
deep_scan.parse_uds_dtcs = parse_uds_dtcs

from final_launcher import main


if __name__ == "__main__":
    main()
