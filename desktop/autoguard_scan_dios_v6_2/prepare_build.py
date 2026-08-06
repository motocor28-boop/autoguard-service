from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def require_markers(path: Path, markers: tuple[str, ...], label: str) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{label}: falta marcador {marker}")


def main() -> None:
    required = [
        ROOT / "app.py",
        ROOT / "final_launcher.py",
        ROOT / "final_dios_app.py",
        ROOT / "final_widgets.py",
        ROOT / "option_b_app.py",
        ROOT / "premium_app.py",
        ROOT / "deep_scan.py",
        ROOT / "deep_scan_full.py",
        ROOT / "diagnostic_parsers.py",
        ROOT / "core.py",
        ROOT / "dtc_database.py",
        ROOT / "reporting.py",
        ROOT / "data" / "autoguard_dtc.sqlite",
        ROOT / "autoguard.ico",
        ROOT / "autoguard.png",
    ]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Faltan archivos para compilar: {', '.join(missing)}")

    require_markers(ROOT / "app.py", ("from final_launcher import main", "diagnostic_parsers"), "Arranque final")
    require_markers(
        ROOT / "final_dios_app.py",
        (
            "6.2.0 FINAL DIOS HD",
            "SENSOR_SYSTEMS",
            "Escaneo profundo",
            "DTC y soluciones",
            "Información del vehículo",
            "Informe Premium",
            "SensorDetailWindow",
            "MultiTraceCanvas",
            "Exportar gráfica",
        ),
        "Interfaz final",
    )
    require_markers(
        ROOT / "final_widgets.py",
        ("enable_windows_dpi_awareness", "class MultiTraceCanvas", "class SensorDetailWindow"),
        "Widgets HD",
    )
    require_markers(
        ROOT / "deep_scan.py",
        ("class DeepScanner", "22F190", "1902FF", "MODE06"),
        "Escaneo profundo",
    )
    require_markers(
        ROOT / "deep_scan_full.py",
        ("class DeepScannerFull", "PID_RAW_", "MODE09_RAW_", "FREEZE_RAW_"),
        "Cobertura máxima",
    )
    require_markers(
        ROOT / "premium_app.py",
        ('APP_AUTHOR = "Esteban Cortez Richards"', 'ORANGE = "#FF7A00"', "Informe PDF Premium"),
        "Base Premium",
    )
    print("Fuente FINAL DIOS HD preparada para compilación Windows")


if __name__ == "__main__":
    main()
