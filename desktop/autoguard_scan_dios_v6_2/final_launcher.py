from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import final_dios_app
import premium_app
from final_widgets import enable_windows_dpi_awareness
from god_premium_app import GOD_BUILD, GOD_VERSION, GodPremiumApp

# Keep all inherited information/help/report pages on the same final version.
final_dios_app.FINAL_VERSION = GOD_VERSION
final_dios_app.FINAL_BUILD = GOD_BUILD
premium_app.APP_VERSION = GOD_VERSION
premium_app.APP_BUILD = GOD_BUILD


def main() -> None:
    enable_windows_dpi_awareness()
    try:
        app = GodPremiumApp()
        app.mainloop()
    except Exception as exc:
        log_dir = Path.home() / "AppData" / "Local" / "Autoguard" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "AUTOGUARD_NIVEL_DIOS_PREMIUM_INICIO_ERROR.log"
        log_file.write_text(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "AUTOGUARD SCAN DIOS",
                f"No fue posible iniciar {GOD_VERSION}.\n\n{exc}\n\nRegistro: {log_file}",
            )
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
