from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    required = [
        ROOT / "app.py", ROOT / "option_b_app.py", ROOT / "premium_app.py",
        ROOT / "deep_scan.py", ROOT / "core.py", ROOT / "dtc_database.py",
        ROOT / "reporting.py", ROOT / "data" / "autoguard_dtc.sqlite",
        ROOT / "autoguard.ico", ROOT / "autoguard.png",
    ]
    missing = [str(path.name) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Faltan archivos para compilar: {', '.join(missing)}")
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    premium_text = (ROOT / "premium_app.py").read_text(encoding="utf-8")
    option_b_text = (ROOT / "option_b_app.py").read_text(encoding="utf-8")
    deep_text = (ROOT / "deep_scan.py").read_text(encoding="utf-8")
    if "from option_b_app import main" not in app_text:
        raise RuntimeError("app.py no inicia la interfaz B autorizada")
    for marker in ("APP_AUTHOR = \"Esteban Cortez Richards\"", "ORANGE = \"#FF7A00\"", "Informe PDF Premium"):
        if marker not in premium_text:
            raise RuntimeError(f"No se encontró marcador Premium: {marker}")
    for marker in ("Escaneo profundo de sistema", "Exportar expediente JSON", "OptionBDeepScanApp"):
        if marker not in option_b_text:
            raise RuntimeError(f"No se encontró marcador de interfaz B: {marker}")
    for marker in ("class DeepScanner", "22F190", "1902FF", "MODE06"):
        if marker not in deep_text:
            raise RuntimeError(f"No se encontró función de escaneo profundo: {marker}")
    print("Fuente Opción B con escaneo profundo preparada para compilación Windows")


if __name__ == "__main__":
    main()
