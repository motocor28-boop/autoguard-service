from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .config import APP_NAME, COLORS, REPORT_DIR


def install_hd_graphs(app_class) -> None:
    if getattr(app_class, "_hd_graphs_installed", False):
        return

    original_build_graph_page = app_class._build_graph_page
    original_update_graph = app_class.update_graph

    def build_graph_page(self) -> None:
        original_build_graph_page(self)
        self.figure.set_dpi(135)
        page = self.pages["Gráficos"]
        export_bar = tk.Frame(page, bg=COLORS["surface_alt"])
        export_bar.pack(fill="x", pady=(7, 0))
        self.graph_stats_label = tk.Label(
            export_bar,
            text="Sin estadísticas registradas",
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=("Segoe UI Semibold", 9),
        )
        self.graph_stats_label.pack(side="left")
        ttk.Button(export_bar, text="Exportar PNG HD", style="Primary.TButton", command=self.save_graph_hd).pack(side="right")
        tk.Label(export_bar, text="220 DPI · listo para informes", bg=COLORS["surface_alt"], fg=COLORS["primary"], font=("Segoe UI", 9)).pack(side="right", padx=(0, 10))

    def update_graph(self) -> None:
        original_update_graph(self)
        name = self.graph_parameter.get() or "RPM motor"
        points = list(self.history.get(name, []))
        self.axes.set_facecolor("#FBFDFF")
        self.axes.grid(True, alpha=0.22, linestyle="--", linewidth=0.7)
        self.axes.set_title(name, loc="left", fontsize=13, fontweight="bold", color=COLORS["nav"], pad=12)
        self.axes.tick_params(colors=COLORS["muted"], labelsize=8)
        self.axes.xaxis.label.set_color(COLORS["muted"])
        self.axes.yaxis.label.set_color(COLORS["muted"])
        for spine in self.axes.spines.values():
            spine.set_color(COLORS["border"])
        for line in self.axes.lines:
            line.set_color(COLORS["primary"])
            line.set_linewidth(2.15)
        for collection in self.axes.collections:
            try:
                collection.set_facecolor(COLORS["primary"])
                collection.set_alpha(0.08)
            except Exception:
                pass
        self.axes.text(
            0.995,
            0.985,
            "AUTOGUARD · SUPERSCAN 2.0",
            transform=self.axes.transAxes,
            ha="right",
            va="top",
            fontsize=7.5,
            color="#90A4B7",
            fontweight="bold",
        )
        if points:
            values = [point[1] for point in points]
            current, minimum, maximum = values[-1], min(values), max(values)
            stats = f"Actual: {current:.2f}   Mínimo: {minimum:.2f}   Máximo: {maximum:.2f}   Muestras: {len(values)}"
            self.axes.text(
                0.012,
                0.975,
                stats,
                transform=self.axes.transAxes,
                ha="left",
                va="top",
                fontsize=8,
                color=COLORS["text"],
                bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": COLORS["border"], "alpha": 0.92},
            )
            if hasattr(self, "graph_stats_label"):
                self.graph_stats_label.configure(text=stats, fg=COLORS["text"])
        elif hasattr(self, "graph_stats_label"):
            self.graph_stats_label.configure(text="Sin estadísticas registradas", fg=COLORS["muted"])
        self.figure.tight_layout()
        self.graph_canvas.draw_idle()

    def save_graph_hd(self) -> None:
        name = self.graph_parameter.get() or "Parametro"
        safe_name = "".join(char if char.isalnum() else "_" for char in name).strip("_") or "Grafico"
        folder = REPORT_DIR / "Graficos_HD"
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / f"{safe_name}_{datetime.now():%Y%m%d_%H%M%S}.png"
        try:
            self.update_graph()
            self.figure.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No fue posible exportar el gráfico HD:\n{exc}")
            return
        self._set_status(f"Gráfico HD exportado: {output.name}")
        messagebox.showinfo(APP_NAME, f"Gráfico HD guardado correctamente:\n{output}")

    app_class._build_graph_page = build_graph_page
    app_class.update_graph = update_graph
    app_class.save_graph_hd = save_graph_hd
    app_class._hd_graphs_installed = True
