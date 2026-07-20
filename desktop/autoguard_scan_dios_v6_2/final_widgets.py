from __future__ import annotations

import csv
import ctypes
import math
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from core import PID_DEFINITIONS, PID_RANGES
from premium_app import BG, GREEN, GRID, MUTED, ORANGE, ORANGE_LIGHT, PANEL, PANEL_2, RED, TEXT, YELLOW

if TYPE_CHECKING:
    from final_dios_app import FinalDiosApp

TRACE_COLORS = (
    "#FF7900",
    "#1E90FF",
    "#58D62C",
    "#BB62F2",
    "#F5B700",
    "#00C8C8",
    "#FF5B15",
    "#E5E7EB",
)

SENSOR_GUIDANCE: dict[int, tuple[str, str, str]] = {
    0x04: (
        "Carga calculada del motor",
        "Porcentaje de carga estimado por la ECU según flujo de aire, presión, posición de acelerador y estrategia interna.",
        "Comparar con RPM, MAF, MAP y acelerador. Una carga incoherente puede orientar a fugas, restricción de admisión o datos erróneos de sensores.",
    ),
    0x05: (
        "Temperatura del refrigerante",
        "Temperatura informada por el sensor ECT. Influye en mezcla, ventiladores, ralentí y protección térmica.",
        "Comparar en frío con temperatura ambiente. Observar calentamiento progresivo y estabilización; confirmar siempre con procedimiento OEM.",
    ),
    0x06: (
        "Corrección corta de combustible",
        "Ajuste inmediato aplicado por la ECU para mantener la mezcla objetivo.",
        "Analizar junto con LTFT, O2/A/F, MAF, MAP y presión de combustible. Valores sostenidos extremos requieren confirmar fugas o suministro.",
    ),
    0x07: (
        "Corrección larga de combustible",
        "Adaptación acumulada de mezcla aprendida por la ECU.",
        "Comparar en ralentí y bajo carga. No borrar adaptativos antes de guardar evidencia y confirmar la causa.",
    ),
    0x0B: (
        "Presión absoluta del múltiple",
        "Presión MAP calculada dentro del múltiple de admisión.",
        "Correlacionar con presión barométrica, RPM, carga y posición de acelerador. Útil para detectar fugas, restricción o problemas de sincronización.",
    ),
    0x0C: (
        "RPM del motor",
        "Velocidad de giro calculada por la ECU a partir de la señal de posición del cigüeñal.",
        "Revisar estabilidad de ralentí, respuesta a aceleración y correlación con carga. La forma de onda CKP directa requiere osciloscopio físico.",
    ),
    0x0D: (
        "Velocidad del vehículo",
        "Velocidad publicada por la ECU o red del vehículo.",
        "Comparar con tablero y sensores de rueda cuando exista acceso al módulo ABS. Diferencias pueden depender de calibración de neumáticos.",
    ),
    0x0F: (
        "Temperatura de aire de admisión",
        "Temperatura del aire medida en la admisión.",
        "Con motor frío debe aproximarse al ambiente. Lecturas extremas pueden afectar densidad calculada y mezcla.",
    ),
    0x10: (
        "Flujo de aire MAF",
        "Masa de aire que ingresa al motor, informada en gramos por segundo.",
        "Comparar con cilindrada, RPM, carga y MAP. Inspeccionar ductos y contaminación antes de condenar el sensor.",
    ),
    0x11: (
        "Posición del acelerador",
        "Apertura del cuerpo de aceleración informada por la ECU.",
        "Comprobar continuidad y correlación con pedal, carga y actuador comandado. Evitar pruebas activas sin procedimiento OEM.",
    ),
    0x2F: (
        "Nivel de combustible",
        "Porcentaje de nivel informado por el módulo que publica el PID estándar 012F.",
        "Comparar con tablero y condición física. Algunos vehículos filtran o no publican este PID.",
    ),
    0x42: (
        "Voltaje del módulo de control",
        "Tensión que la ECU informa en su alimentación interna.",
        "Comparar con multímetro en batería y ECU. Diferencias pueden indicar caída de tensión, masa deficiente o medición interna.",
    ),
    0x5C: (
        "Temperatura de aceite del motor",
        "Temperatura de aceite publicada mediante PID estándar cuando está soportado.",
        "Confirmar tendencia con ECT y condiciones de carga. No todos los vehículos publican este parámetro.",
    ),
    0x5E: (
        "Flujo de combustible",
        "Consumo instantáneo informado directamente por PID 015E cuando la ECU lo soporta.",
        "Distinguir lectura directa de estimación MAF. Comparar tendencia bajo carga; no reemplaza medición física de presión y caudal.",
    ),
}


def enable_windows_dpi_awareness() -> None:
    """Request per-monitor DPI awareness before Tk creates the main window."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def format_value(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1000:
        return f"{value:.0f}"
    if absolute >= 100:
        return f"{value:.1f}"
    return f"{value:.2f}"


class MultiTraceCanvas(tk.Canvas):
    """Vector multi-channel OBD telemetry display inspired by workshop scopes."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            bg="#050A0F",
            highlightthickness=1,
            highlightbackground="#2A3947",
            **kwargs,
        )
        self.owner: FinalDiosApp | None = None
        self.pids: list[int] = []
        self.paused = False
        self.seconds = 10.0
        self.bind("<Configure>", lambda _event: self.redraw())

    def bind_owner(self, owner: FinalDiosApp) -> None:
        self.owner = owner

    def set_pids(self, pids: list[int]) -> None:
        self.pids = pids[:8]
        self.redraw()

    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        if not paused:
            self.redraw()

    def set_time_window(self, seconds: float) -> None:
        self.seconds = max(2.0, min(float(seconds), 120.0))
        self.redraw()

    def redraw(self) -> None:
        if self.paused:
            return
        self.delete("all")
        width = max(640, self.winfo_width())
        height = max(340, self.winfo_height())
        left, right, top, bottom = 42, 15, 22, 30
        plot_w = width - left - right
        plot_h = height - top - bottom

        for index in range(11):
            x = left + plot_w * index / 10
            self.create_line(x, top, x, top + plot_h, fill=GRID, width=1)
            label = -self.seconds + self.seconds * index / 10
            self.create_text(x, height - 12, text=f"{label:.0f}s", fill=MUTED, font=("Segoe UI", 8))
        horizontal = max(4, len(self.pids) + 1)
        for index in range(horizontal + 1):
            y = top + plot_h * index / horizontal
            self.create_line(left, y, left + plot_w, y, fill=GRID, width=1)

        if self.owner is None or not self.pids:
            self.create_text(width / 2, height / 2, text="Seleccione sensores e inicie la lectura", fill=MUTED, font=("Segoe UI", 13))
            return

        now = time.time()
        cutoff = now - self.seconds
        lanes = max(1, len(self.pids))
        lane_h = plot_h / lanes
        for lane, pid in enumerate(self.pids):
            samples = [item for item in self.owner.history.get(pid, []) if item[0] >= cutoff]
            name, unit = PID_DEFINITIONS.get(pid, (f"PID 01{pid:02X}", ""))
            color = TRACE_COLORS[lane % len(TRACE_COLORS)]
            lane_top = top + lane * lane_h
            center = lane_top + lane_h / 2
            self.create_text(5, center, anchor="w", text=str(lane + 1), fill=color, font=("Segoe UI", 8, "bold"))
            if len(samples) < 2:
                self.create_text(left + 8, center, anchor="w", text=f"{name} · esperando datos", fill=MUTED, font=("Segoe UI", 8))
                continue
            values = [float(value) for _, value in samples]
            minimum = min(values)
            maximum = max(values)
            span = max(maximum - minimum, 0.001)
            usable = lane_h * 0.68
            points: list[float] = []
            for timestamp, value in samples:
                x = left + max(0.0, min(1.0, (timestamp - cutoff) / self.seconds)) * plot_w
                normalized = (float(value) - minimum) / span
                y = center + usable / 2 - normalized * usable
                points.extend((x, y))
            if len(points) >= 4:
                self.create_line(*points, fill=color, width=2, smooth=False)
            latest = values[-1]
            self.create_text(
                left + 6,
                lane_top + 8,
                anchor="nw",
                text=f"{name}  {format_value(latest)} {unit}",
                fill=color,
                font=("Segoe UI", 8, "bold"),
            )
        marker_x = left + plot_w
        self.create_line(marker_x, top, marker_x, top + plot_h, fill="#D8DEE6", dash=(3, 2), width=1)


class SensorDetailWindow(tk.Toplevel):
    """Dedicated real-time window for one sensor, with graph and diagnostics."""

    def __init__(self, owner: FinalDiosApp, pid: int) -> None:
        super().__init__(owner)
        self.owner = owner
        self.pid = pid
        self.name, self.unit = PID_DEFINITIONS.get(pid, (f"PID 01{pid:02X}", ""))
        self.title(f"AUTOGUARD · {self.name} · PID 01{pid:02X}")
        self.geometry("1080x700")
        self.minsize(840, 560)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self.after(180, self._refresh)

    def _build(self) -> None:
        header = tk.Frame(self, bg="#070C12", highlightbackground="#273544", highlightthickness=1)
        header.pack(fill="x", padx=10, pady=10)
        left = tk.Frame(header, bg="#070C12")
        left.pack(side="left", padx=16, pady=12)
        tk.Label(left, text=self.name, bg="#070C12", fg=ORANGE, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(left, text=f"PID 01{self.pid:02X} · Ventana individual de lectura", bg="#070C12", fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.value_label = tk.Label(header, text="--", bg="#070C12", fg=ORANGE_LIGHT, font=("Segoe UI", 30, "bold"))
        self.value_label.pack(side="right", padx=(8, 18), pady=10)
        self.unit_label = tk.Label(header, text=self.unit, bg="#070C12", fg=TEXT, font=("Segoe UI", 12, "bold"))
        self.unit_label.pack(side="right", pady=(26, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        graph_panel = tk.Frame(body, bg=PANEL, highlightbackground="#304050", highlightthickness=1)
        graph_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        info_panel = tk.Frame(body, bg=PANEL, highlightbackground="#304050", highlightthickness=1)
        info_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        toolbar = tk.Frame(graph_panel, bg=PANEL)
        toolbar.pack(fill="x", padx=12, pady=8)
        tk.Label(toolbar, text="GRÁFICO EN TIEMPO REAL", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(toolbar, text="Exportar CSV", command=self._export_csv).pack(side="right")
        self.graph = tk.Canvas(graph_panel, bg="#05090E", highlightthickness=0)
        self.graph.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.graph.bind("<Configure>", lambda _event: self._draw_graph())

        stats = tk.Frame(info_panel, bg=PANEL)
        stats.pack(fill="x", padx=12, pady=12)
        self.stat_labels: dict[str, tk.Label] = {}
        for index, key in enumerate(("Actual", "Mínimo", "Promedio", "Máximo")):
            card = tk.Frame(stats, bg=PANEL_2, highlightbackground="#354454", highlightthickness=1)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=4, pady=4)
            stats.columnconfigure(index % 2, weight=1)
            tk.Label(card, text=key.upper(), bg=PANEL_2, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=9, pady=(8, 2))
            label = tk.Label(card, text="--", bg=PANEL_2, fg=ORANGE_LIGHT, font=("Segoe UI", 16, "bold"))
            label.pack(anchor="w", padx=9, pady=(0, 8))
            self.stat_labels[key] = label

        title, description, diagnostic = SENSOR_GUIDANCE.get(
            self.pid,
            (
                self.name,
                "Parámetro publicado por la ECU. Su disponibilidad y significado exacto pueden variar según fabricante y estrategia de control.",
                "Comparar con parámetros relacionados, condiciones de operación y documentación OEM antes de reemplazar componentes.",
            ),
        )
        tk.Label(info_panel, text="DESCRIPCIÓN TÉCNICA", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Label(info_panel, text=description, bg=PANEL, fg=TEXT, wraplength=360, justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=14)
        tk.Label(info_panel, text="USO DIAGNÓSTICO", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(info_panel, text=diagnostic, bg=PANEL, fg=TEXT, wraplength=360, justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=14)
        self.state_label = tk.Label(info_panel, text="Estado: esperando señal ECU", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.state_label.pack(anchor="w", padx=14, pady=16)

    def _refresh(self) -> None:
        if not self.winfo_exists():
            return
        values = [float(value) for _, value in self.owner.history.get(self.pid, [])]
        if values:
            current = values[-1]
            self.value_label.configure(text=format_value(current))
            self.stat_labels["Actual"].configure(text=f"{format_value(current)} {self.unit}")
            self.stat_labels["Mínimo"].configure(text=f"{format_value(min(values))} {self.unit}")
            self.stat_labels["Promedio"].configure(text=f"{format_value(sum(values) / len(values))} {self.unit}")
            self.stat_labels["Máximo"].configure(text=f"{format_value(max(values))} {self.unit}")
            self.state_label.configure(text="Estado: señal recibida", fg=GREEN)
        else:
            self.state_label.configure(text="Estado: esperando señal ECU", fg=MUTED)
        self._draw_graph()
        self.after(180, self._refresh)

    def _draw_graph(self) -> None:
        canvas = self.graph
        canvas.delete("all")
        width = max(480, canvas.winfo_width())
        height = max(300, canvas.winfo_height())
        left, right, top, bottom = 50, 18, 24, 34
        plot_w, plot_h = width - left - right, height - top - bottom
        for index in range(11):
            x = left + plot_w * index / 10
            canvas.create_line(x, top, x, top + plot_h, fill=GRID)
        for index in range(9):
            y = top + plot_h * index / 8
            canvas.create_line(left, y, left + plot_w, y, fill=GRID)
        now = time.time()
        samples = [item for item in self.owner.history.get(self.pid, []) if item[0] >= now - 30]
        if len(samples) < 2:
            canvas.create_text(width / 2, height / 2, text="Esperando muestras...", fill=MUTED, font=("Segoe UI", 12))
            return
        values = [float(value) for _, value in samples]
        minimum = min(values)
        maximum = max(values)
        span = max(maximum - minimum, 0.001)
        points: list[float] = []
        for timestamp, value in samples:
            x = left + (timestamp - (now - 30)) / 30 * plot_w
            y = top + plot_h - (float(value) - minimum) / span * plot_h
            points.extend((x, y))
        canvas.create_line(*points, fill=ORANGE, width=3)
        canvas.create_text(6, top, anchor="w", text=f"{maximum:.2f}", fill=MUTED, font=("Consolas", 8))
        canvas.create_text(6, top + plot_h, anchor="w", text=f"{minimum:.2f}", fill=MUTED, font=("Consolas", 8))
        canvas.create_text(left, 10, anchor="w", text=f"Últimos 30 s · {self.name}", fill=TEXT, font=("Segoe UI", 9, "bold"))

    def _export_csv(self) -> None:
        samples = list(self.owner.history.get(self.pid, []))
        if not samples:
            messagebox.showinfo("Exportar sensor", "No existen muestras registradas.", parent=self)
            return
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar sensor",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"AUTOGUARD_PID_01{self.pid:02X}.csv",
        )
        if not target:
            return
        with Path(target).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["fecha_hora", "pid", "sensor", "valor", "unidad"])
            for timestamp, value in samples:
                writer.writerow([
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
                    f"01{self.pid:02X}",
                    self.name,
                    f"{float(value):.5f}",
                    self.unit,
                ])
        messagebox.showinfo("Exportación", f"Sensor exportado en:\n{target}", parent=self)

    def _close(self) -> None:
        self.owner.sensor_windows.pop(self.pid, None)
        self.destroy()
