from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    required = [
        ROOT / "app.py", ROOT / "premium_app.py", ROOT / "core.py",
        ROOT / "dtc_database.py", ROOT / "reporting.py",
        ROOT / "data" / "autoguard_dtc.sqlite",
        ROOT / "autoguard.ico", ROOT / "autoguard.png",
    ]
    missing = [str(path.name) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Faltan archivos para compilar: {', '.join(missing)}")
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    premium_text = (ROOT / "premium_app.py").read_text(encoding="utf-8")
    if "from premium_app import main" not in app_text:
        raise RuntimeError("app.py no inicia la interfaz Premium")
    for marker in ("APP_AUTHOR = \"Esteban Cortez Richards\"", "ORANGE = \"#FF7A00\"", "Informe PDF Premium"):
        if marker not in premium_text:
            raise RuntimeError(f"No se encontró marcador Premium: {marker}")
    print("Fuente Premium preparada para compilación Windows")


if __name__ == "__main__":
    main()
