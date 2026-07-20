import deep_scan
import option_b_app
from diagnostic_parsers import decode_printable, extract_after_marker, parse_uds_ascii, parse_uds_dtcs

# Replace the basic concatenation parser with the ISO-TP-aware implementation
# before importing the maximum-coverage scanner.
deep_scan._extract_after_marker = extract_after_marker
deep_scan._decode_printable = decode_printable
deep_scan.parse_uds_ascii = parse_uds_ascii
deep_scan.parse_uds_dtcs = parse_uds_dtcs

from deep_scan_full import DeepScannerFull

option_b_app.DeepScanner = DeepScannerFull
main = option_b_app.main


if __name__ == "__main__":
    main()
