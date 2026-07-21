from __future__ import annotations

import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import final_dios_app
import premium_app
from core import estimate_fuel_rate_from_maf
from final_widgets import enable_windows_dpi_awareness
from optimized_navigation_app import (
    NAV_BUILD,
    NAV_VERSION,
    OptimizedNavigationApp,
    run_navigation_self_test,
)

# Keep inherited information, reports and help pages on the same final version.
final_dios_app.FINAL_VERSION = NAV_VERSION
final_dios_app.FINAL_BUILD = NAV_BUILD
premium_app.APP_VERSION = NAV_VERSION
premium_app.APP_BUILD = NAV_BUILD
# Compatibility for the navigation layer's fuel-flow calculation.
premium_app.estimate_fuel_rate_from_maf = estimate_fuel_rate_from_maf


def _write_startup_log(exc: Exception, suffix: str = "INICIO_ERROR") -> Path:
    log_dir = Path.home() / "AppData" / "Local" / "Autoguard" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"AUTOGUARD_NAVEGACION_PREMIUM_{suffix}.log"
    log_file.write_text(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )
    return log_file


def main() -> None:
    enable_windows_dpi_awareness()

    if "--autoguard-self-test" in sys.argv:
        try:
            # Marcador reservado exclusivamente para comprobar en CI que el
            # instalador restaura la versión anterior cuando la autoprueba falla.
            force_failure = Path.cwd() / ".autoguard_ci_force_self_test_failure"
            if force_failure.exists():
                raise RuntimeError("Fallo controlado de autoprueba para validar rollback")
            run_navigation_self_test()
            return
        except Exception as exc:
            _write_startup_log(exc, "AUTOPRUEBA_ERROR")
            raise

    try:
        app = OptimizedNavigationApp()
        app.mainloop()
    except Exception as exc:
        log_file = _write_startup_log(exc)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "AUTOGUARD SCAN DIOS",
                f"No fue posible iniciar {NAV_VERSION}.\n\n{exc}\n\nRegistro: {log_file}",
            )
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
