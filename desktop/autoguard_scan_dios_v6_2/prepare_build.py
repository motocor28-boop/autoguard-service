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
        ROOT / "navigation_premium_app.py",
        ROOT / "god_premium_app.py",
        ROOT / "premium_gauges.py",
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
        ROOT / "autoguard_icon.png",
    ]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Faltan archivos para compilar: {', '.join(missing)}")

    require_markers(ROOT / "app.py", ("from final_launcher import main", "diagnostic_parsers"), "Arranque final")
    require_markers(
        ROOT / "final_launcher.py",
        ("NavigationPremiumApp", "NAV_VERSION", "enable_windows_dpi_awareness"),
        "Lanzador final",
    )
    require_markers(
        ROOT / "navigation_premium_app.py",
        (
            "6.2.2 NIVEL DIOS PREMIUM",
            "MENÚ PRINCIPAL",
            "Sensores por sistema",
            "MODO ESCÁNER",
            "SALIR PANTALLA COMPLETA",
            "DATOS DEL VEHÍCULO",
            "class NavigationPremiumApp",
        ),
        "Navegación separada",
    )
    require_markers(
        ROOT / "god_premium_app.py",
        (
            "Osciloscopio ECU",
            "Escaneo y códigos",
            "Sin códigos activos",
            "CÓDIGOS BORRADOS DURANTE LA SESIÓN",
            "Borrado confirmado por ECU",
        ),
        "Diagnóstico limpio Nivel Dios",
    )
    require_markers(
        ROOT / "premium_gauges.py",
        ("class RealisticGauge", "Dedicated digital display", "41 clean ticks"),
        "Relojes realistas",
    )
    require_markers(
        ROOT / "final_dios_app.py",
        ("SENSOR_SYSTEMS", "SensorDetailWindow", "MultiTraceCanvas", "Exportar gráfica"),
        "Base de interfaz Full HD",
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
    require_markers(
        ROOT / "make_icon.py",
        ("AUTO GUARD", "SERVICE", "TU VEHÍCULO, NUESTRA PRIORIDAD", "autoguard.ico"),
        "Branding oficial",
    )
    print("Fuente NIVEL DIOS PREMIUM con navegación por páginas preparada para Windows")


if __name__ == "__main__":
    main()
