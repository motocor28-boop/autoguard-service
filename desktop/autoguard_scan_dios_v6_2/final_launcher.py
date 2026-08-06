from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from final_dios_app import FinalDiosApp, FINAL_VERSION
from final_widgets import enable_windows_dpi_awareness
from premium_app import APP_AUTHOR, MUTED, ORANGE, ORANGE_LIGHT


def build_sidebar_fixed(self: FinalDiosApp) -> None:
    """Build the approved narrow sidebar inside PremiumApp's existing frame."""
    self.sidebar.configure(bg="#080D13", width=124, highlightbackground="#283542", highlightthickness=1)
    self.sidebar.pack_propagate(False)
    for child in self.sidebar.winfo_children():
        child.destroy()

    brand = tk.Frame(self.sidebar, bg="#080D13")
    brand.pack(fill="x", pady=(10, 12))
    tk.Label(brand, text="A", bg=ORANGE, fg="#FFFFFF", font=("Segoe UI", 18, "bold"), width=3, height=1).pack(pady=(0, 5))
    tk.Label(brand, text="AUTOGUARD", bg="#080D13", fg=ORANGE, font=("Segoe UI", 8, "bold")).pack()
    tk.Label(brand, text="SCAN DIOS", bg="#080D13", fg=MUTED, font=("Segoe UI", 7, "bold")).pack()

    self.nav_buttons = {}
    menu = [
        ("Datos en vivo", "⌁", "Datos en vivo\ny Osciloscopio"),
        ("Escaneo profundo", "◎", "Escaneo\nprofundo"),
        ("DTC y soluciones", "⚠", "Diagnóstico\nDTC"),
        ("Pruebas funcionales", "▦", "Tablas y\nPruebas"),
        ("Módulos ECU", "▣", "Módulos\nECU"),
        ("Información", "▤", "Planificación\ny Base Local"),
        ("Información del vehículo", "▱", "Información\ndel vehículo"),
        ("Informe Premium", "PDF", "Informe\nPremium"),
        ("Historial", "◷", "Historial\ny registros"),
        ("Conexión", "⚙", "Ajustes"),
        ("Ayuda", "?", "Ayuda"),
    ]
    for page, icon, label in menu:
        button = tk.Button(
            self.sidebar,
            text=f"{icon}\n{label}",
            relief="flat",
            bd=0,
            bg="#080D13",
            fg="#AEB8C4",
            activebackground="#18222E",
            activeforeground=ORANGE_LIGHT,
            font=("Segoe UI", 8, "bold"),
            padx=4,
            pady=7,
            justify="center",
            command=lambda target=page: self._show_page(target),
        )
        button.pack(fill="x", padx=4, pady=1)
        self.nav_buttons[page] = button

    footer = tk.Frame(self.sidebar, bg="#080D13")
    footer.pack(side="bottom", fill="x", padx=6, pady=8)
    self.side_connection = tk.Label(footer, text="● SIN CONEXIÓN", bg="#080D13", fg=MUTED, font=("Segoe UI", 7, "bold"), wraplength=105)
    self.side_connection.pack()
    tk.Label(footer, text=f"Autor\n{APP_AUTHOR}", bg="#080D13", fg="#697786", font=("Segoe UI", 6), justify="center").pack(pady=(6, 0))


FinalDiosApp._build_sidebar = build_sidebar_fixed


def main() -> None:
    enable_windows_dpi_awareness()
    try:
        app = FinalDiosApp()
        app.mainloop()
    except Exception as exc:
        log_dir = Path.home() / "AppData" / "Local" / "Autoguard" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "AUTOGUARD_FINAL_DIOS_INICIO_ERROR.log"
        log_file.write_text(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "AUTOGUARD SCAN DIOS",
                f"No fue posible iniciar {FINAL_VERSION}.\n\n{exc}\n\nRegistro: {log_file}",
            )
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
