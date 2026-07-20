from __future__ import annotations

import math
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from core import ConnectionConfig, ELM327Client, LiveDataWorker, PID_DEFINITIONS
from dtc_database import DTCRecord, DtcDatabase, resource_path
from reporting import default_report_path, generate_pdf_report

APP_NAME = "AUTOGUARD SCAN DIOS"
APP_VERSION = "6.2"
APP_BUILD = "Nueva base limpia 2026.07"
APP_AUTHOR = "Esteban Cortez Richards"

BG = "#0F141B"
PANEL = "#171E28"
PANEL_2 = "#202A36"
TEXT = "#F3F5F7"
MUTED = "#A6B0BD"
RED = "#E10600"
GREEN = "#2AC769"
YELLOW = "#F4B942"
BLUE = "#3D8BFF"
GRID = "#2D3948"


def open_path(path: Path) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except AttributeError:
        subprocess.Popen(["xdg-open", str(path)])


class Gauge(tk.Canvas):
    def __init__(
        self,
        master,
        title: str,
        unit: str,
        minimum: float,
        maximum: float,
        warning: float,
        danger: float,
        size: int = 235,
    ) -> None:
        super().__init__(master, width=size, height=size, bg=PANEL, highlightthickness=0)
        self.title = title
        self.unit = unit
        self.minimum = minimum
        self.maximum = maximum
        self.warning = warning
        self.danger = danger
        self.size = size
        self.value = minimum
        self.signal = False
        self.bind("<Configure>", lambda _event: self.draw())
        self.draw()

    def set_value(self, value: float, signal: bool = True) -> None:
        self.value = max(self.minimum, min(self.maximum, float(value)))
        self.signal = signal
        self.draw()

    def _angle_for(self, value: float) -> float:
        ratio = (value - self.minimum) / (self.maximum - self.minimum)
        return math.radians(225.0 - ratio * 270.0)

    def draw(self) -> None:
        self.delete("all")
        w = max(180, self.winfo_width())
        h = max(180, self.winfo_height())
        size = min(w, h)
        cx, cy = w / 2, h / 2
        radius = size * 0.43

        # Metallic bezel and high-contrast face.
        for offset, color in ((0, "#77818D"), (4, "#343C47"), (9, "#0A0E13"), (14, "#151B23")):
            self.create_oval(
                cx - radius + offset,
                cy - radius + offset,
                cx + radius - offset,
                cy + radius - offset,
                fill=color,
                outline=color,
            )

        # Warning zones.
        def arc(start_value: float, end_value: float, color: str, width: int = 8) -> None:
            start_angle = 225.0 - ((start_value - self.minimum) / (self.maximum - self.minimum)) * 270.0
            end_angle = 225.0 - ((end_value - self.minimum) / (self.maximum - self.minimum)) * 270.0
            self.create_arc(
                cx - radius + 22,
                cy - radius + 22,
                cx + radius - 22,
                cy + radius - 22,
                start=end_angle,
                extent=start_angle - end_angle,
                style="arc",
                outline=color,
                width=width,
            )

        arc(self.warning, self.danger, YELLOW)
        arc(self.danger, self.maximum, RED)

        tick_radius_outer = radius - 27
        for index in range(51):
            ratio = index / 50.0
            value = self.minimum + ratio * (self.maximum - self.minimum)
            angle = self._angle_for(value)
            major = index % 5 == 0
            length = 13 if major else 6
            width_line = 2 if major else 1
            inner = tick_radius_outer - length
            x1 = cx + math.cos(angle) * inner
            y1 = cy - math.sin(angle) * inner
            x2 = cx + math.cos(angle) * tick_radius_outer
            y2 = cy - math.sin(angle) * tick_radius_outer
            color = "#F2F5F7" if value < self.warning else (YELLOW if value < self.danger else RED)
            self.create_line(x1, y1, x2, y2, fill=color, width=width_line)
            if major:
                label_radius = inner - 14
                lx = cx + math.cos(angle) * label_radius
                ly = cy - math.sin(angle) * label_radius
                if self.maximum >= 1000:
                    text = f"{value / 1000:.0f}"
                else:
                    text = f"{value:.0f}"
                self.create_text(lx, ly, text=text, fill=MUTED, font=("Segoe UI", 8, "bold"))

        # Needle.
        angle = self._angle_for(self.value)
        needle_length = radius - 52
        nx = cx + math.cos(angle) * needle_length
        ny = cy - math.sin(angle) * needle_length
        self.create_line(cx, cy, nx, ny, fill=RED, width=4, arrow="last", arrowshape=(10, 12, 4))
        self.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#C9D0D7", outline="#05070A", width=2)

        self.create_text(cx, cy + radius * 0.34, text=self.title, fill=TEXT, font=("Segoe UI", 11, "bold"))
        self.create_rectangle(cx - 55, cy + radius * 0.46, cx + 55, cy + radius * 0.70, fill="#06090D", outline="#4B5664")
        if abs(self.value) >= 100:
            value_text = f"{self.value:.0f}"
        else:
            value_text = f"{self.value:.1f}"
        self.create_text(cx, cy + radius * 0.56, text=value_text, fill="#E7F5EA", font=("Consolas", 15, "bold"))
        self.create_text(cx, cy + radius * 0.74, text=self.unit, fill=MUTED, font=("Segoe UI", 8))
        signal_color = GREEN if self.signal else "#505B67"
        self.create_oval(cx + radius * 0.52, cy - radius * 0.50, cx + radius * 0.62, cy - radius * 0.40, fill=signal_color, outline="")
        self.create_text(cx + radius * 0.38, cy - radius * 0.45, text="RX", fill=MUTED, font=("Segoe UI", 7, "bold"))


class ScopeCanvas(tk.Canvas):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, bg="#070B10", highlightthickness=1, highlightbackground="#3B4654", **kwargs)
        self.samples: deque[float] = deque(maxlen=300)
        self.minimum = 0.0
        self.maximum = 100.0
        self.title = "Sin señal"
        self.unit = ""
        self.bind("<Configure>", lambda _event: self.redraw())

    def configure_signal(self, title: str, unit: str, minimum: float, maximum: float) -> None:
        self.title = title
        self.unit = unit
        self.minimum = minimum
        self.maximum = max(maximum, minimum + 0.001)
        self.samples.clear()
        self.redraw()

    def add_sample(self, value: float) -> None:
        self.samples.append(float(value))
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        w = max(400, self.winfo_width())
        h = max(250, self.winfo_height())
        margin = 42
        for i in range(11):
            x = margin + (w - 2 * margin) * i / 10
            self.create_line(x, margin, x, h - margin, fill=GRID, width=1)
        for i in range(9):
            y = margin + (h - 2 * margin) * i / 8
            self.create_line(margin, y, w - margin, y, fill=GRID, width=1)
        self.create_text(margin, 18, anchor="w", text=f"{self.title} [{self.unit}]", fill=TEXT, font=("Segoe UI", 11, "bold"))
        self.create_text(w - margin, 18, anchor="e", text="Telemetría ECU OBD-II", fill=MUTED, font=("Segoe UI", 9))
        if len(self.samples) < 2:
            self.create_text(w / 2, h / 2, text="Esperando muestras...", fill=MUTED, font=("Segoe UI", 13))
            return
        values = list(self.samples)
        local_min = min(self.minimum, min(values))
        local_max = max(self.maximum, max(values))
        span = max(local_max - local_min, 0.001)
        points: list[float] = []
        for index, value in enumerate(values):
            x = margin + (w - 2 * margin) * index / max(len(values) - 1, 1)
            y = h - margin - (value - local_min) / span * (h - 2 * margin)
            points.extend((x, y))
        self.create_line(*points, fill="#30E67B", width=2, smooth=False)
        self.create_text(5, margin, anchor="w", text=f"{local_max:.1f}", fill=MUTED, font=("Consolas", 8))
        self.create_text(5, h - margin, anchor="w", text=f"{local_min:.1f}", fill=MUTED, font=("Consolas", 8))


class AutoguardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1450x880")
        self.minsize(1180, 720)
        self.configure(bg=BG)
        try:
            self.iconbitmap(resource_path("autoguard.ico"))
        except Exception:
            pass

        self.ui_events: "queue.Queue[tuple]" = queue.Queue()
        self.data_events: "queue.Queue[dict]" = queue.Queue()
        self.client = ELM327Client(log=lambda message: self.ui_events.put(("log", message)))
        self.live_worker: LiveDataWorker | None = None
        self.latest_values: dict[int, float] = {}
        self.current_dtcs: list[dict[str, str]] = []
        self.fuel_source = "No disponible"
        self.supported_pids: set[int] = set()
        self.database = DtcDatabase()
        self.db_stats = self.database.stats()

        self._configure_style()
        self._build_header()
        self._build_notebook()
        self._build_statusbar()
        self.after(80, self._drain_queues)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 19, "bold"))
        style.configure("Accent.TLabel", background=BG, foreground=RED, font=("Segoe UI", 11, "bold"))
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL_2, foreground=TEXT, padding=(13, 8), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", RED)], foreground=[("selected", "white")])
        style.configure("TButton", background=PANEL_2, foreground=TEXT, padding=(10, 6), font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", "#384657")])
        style.configure("Accent.TButton", background=RED, foreground="white", padding=(12, 7))
        style.map("Accent.TButton", background=[("active", "#B80500")])
        style.configure("Treeview", background="#111821", fieldbackground="#111821", foreground=TEXT, rowheight=27, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#303B49", foreground="white", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#244E7E")])
        style.configure("TEntry", fieldbackground="#0E141C", foreground=TEXT)
        style.configure("TCombobox", fieldbackground="#0E141C", foreground=TEXT)
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", PANEL)])

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(18, 12))
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"v{APP_VERSION} · {APP_BUILD}", style="Accent.TLabel").pack(side="left", padx=14)
        right = ttk.Frame(header)
        right.pack(side="right")
        self.connection_indicator = tk.Canvas(right, width=16, height=16, bg=BG, highlightthickness=0)
        self.connection_indicator.pack(side="left", padx=(0, 7))
        self.connection_indicator.create_oval(2, 2, 14, 14, fill="#59636E", outline="", tags="dot")
        self.header_status = ttk.Label(right, text="Sin conexión", foreground=MUTED)
        self.header_status.pack(side="left")

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.tab_home = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_connection = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_dtc = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_live = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_scope = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_tests = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_console = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_report = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        self.tab_info = ttk.Frame(self.notebook, style="Panel.TFrame", padding=14)
        for frame, title in (
            (self.tab_home, "Panel DIOS"),
            (self.tab_connection, "Conexión"),
            (self.tab_dtc, "DTC"),
            (self.tab_live, "Datos en vivo"),
            (self.tab_scope, "Osciloscopio"),
            (self.tab_tests, "Pruebas funcionales"),
            (self.tab_console, "Consola"),
            (self.tab_report, "Informe PDF"),
            (self.tab_info, "Información y planificación"),
        ):
            self.notebook.add(frame, text=title)
        self._build_home()
        self._build_connection()
        self._build_dtc()
        self._build_live()
        self._build_scope()
        self._build_tests()
        self._build_console()
        self._build_report()
        self._build_info()

    def _panel(self, parent, title: str) -> ttk.Frame:
        outer = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        ttk.Label(outer, text=title, style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        return outer

    def _build_home(self) -> None:
        top = ttk.Frame(self.tab_home, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="PANEL DIOS · TELEMETRÍA PRINCIPAL", style="Panel.TLabel", font=("Segoe UI", 13, "bold")).pack(side="left")
        self.protocol_label = ttk.Label(top, text="Protocolo: Sin conexión", style="Muted.TLabel")
        self.protocol_label.pack(side="right")

        gauges = ttk.Frame(self.tab_home, style="Panel.TFrame")
        gauges.pack(fill="x", expand=False, pady=12)
        for column in range(4):
            gauges.columnconfigure(column, weight=1)
        self.gauge_rpm = Gauge(gauges, "RPM", "rpm", 0, 7000, 5000, 6200)
        self.gauge_speed = Gauge(gauges, "VELOCIDAD", "km/h", 0, 240, 160, 210)
        self.gauge_temp = Gauge(gauges, "REFRIGERANTE", "°C", 40, 130, 100, 115)
        self.gauge_voltage = Gauge(gauges, "BATERÍA", "V", 8, 18, 15.2, 16.5)
        for index, gauge in enumerate((self.gauge_rpm, self.gauge_speed, self.gauge_temp, self.gauge_voltage)):
            gauge.grid(row=0, column=index, padx=8, sticky="nsew")

        lower = ttk.Frame(self.tab_home, style="Panel.TFrame")
        lower.pack(fill="both", expand=True)
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)
        summary = self._panel(lower, "Resumen de sesión")
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.session_summary = tk.Text(summary, height=9, bg="#0D131B", fg=TEXT, insertbackground=TEXT, relief="flat", font=("Consolas", 10))
        self.session_summary.pack(fill="both", expand=True)
        self.session_summary.insert("end", "AUTOGUARD listo. Seleccione Conexión para iniciar.\n")
        self.session_summary.configure(state="disabled")
        database = self._panel(lower, "Cobertura offline")
        database.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        stats_text = (
            f"Códigos DTC únicos: {self.db_stats['unique_codes']:,}\n"
            f"Definiciones: {self.db_stats['definitions']:,}\n"
            f"Fabricantes específicos: {self.db_stats['manufacturers']}\n"
            "Código de control U0123: disponible\n\n"
            "La interpretación específica debe confirmarse por marca, modelo, año, VIN y documentación OEM."
        ).replace(",", ".")
        ttk.Label(database, text=stats_text, style="Panel.TLabel", justify="left", font=("Segoe UI", 11)).pack(anchor="nw")

    def _build_connection(self) -> None:
        content = ttk.Frame(self.tab_connection, style="Panel.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        labels = ["Modo", "Puerto COM", "Baudrate", "Host WiFi", "Puerto WiFi", "Timeout"]
        self.mode_var = tk.StringVar(value="Simulador")
        self.com_var = tk.StringVar(value="COM3")
        self.baud_var = tk.StringVar(value="38400")
        self.host_var = tk.StringVar(value="192.168.0.10")
        self.wifi_port_var = tk.StringVar(value="35000")
        self.timeout_var = tk.StringVar(value="2.0")
        values = [self.mode_var, self.com_var, self.baud_var, self.host_var, self.wifi_port_var, self.timeout_var]
        for row, (label, variable) in enumerate(zip(labels, values)):
            ttk.Label(content, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
            if row == 0:
                widget = ttk.Combobox(content, textvariable=variable, values=["Simulador", "COM", "WiFi"], state="readonly", width=35)
            elif row == 1:
                self.com_combo = ttk.Combobox(content, textvariable=variable, values=ELM327Client.available_serial_ports(), width=35)
                widget = self.com_combo
            else:
                widget = ttk.Entry(content, textvariable=variable, width=38)
            widget.grid(row=row, column=1, sticky="ew", pady=6)
        buttons = ttk.Frame(content, style="Panel.TFrame")
        buttons.grid(row=6, column=0, columnspan=2, sticky="w", pady=16)
        ttk.Button(buttons, text="Actualizar puertos", command=self._refresh_ports).pack(side="left", padx=(0, 8))
        self.connect_button = ttk.Button(buttons, text="Conectar", style="Accent.TButton", command=self._connect)
        self.connect_button.pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Desconectar", command=self._disconnect).pack(side="left")
        self.connection_detail = ttk.Label(content, text="Estado: sin conexión", style="Panel.TLabel", font=("Segoe UI", 11, "bold"))
        self.connection_detail.grid(row=7, column=0, columnspan=2, sticky="w", pady=10)
        info = (
            "WiFi: use la IP y puerto configurados en el adaptador ELM327.\n"
            "COM: seleccione el puerto Bluetooth/USB y el baudrate del adaptador.\n"
            "Simulador: permite validar la interfaz, informes, DTC y gráficos sin vehículo."
        )
        ttk.Label(content, text=info, style="Muted.TLabel", justify="left").grid(row=8, column=0, columnspan=2, sticky="w", pady=12)

    def _build_dtc(self) -> None:
        toolbar = ttk.Frame(self.tab_dtc, style="Panel.TFrame")
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Escaneo completo", style="Accent.TButton", command=self._scan_dtcs).pack(side="left", padx=(0, 7))
        ttk.Button(toolbar, text="Borrar DTC", command=self._clear_dtcs).pack(side="left", padx=(0, 16))
        ttk.Label(toolbar, text="Buscar código o descripción:", style="Panel.TLabel").pack(side="left")
        self.dtc_search_var = tk.StringVar(value="U0123")
        entry = ttk.Entry(toolbar, textvariable=self.dtc_search_var, width=24)
        entry.pack(side="left", padx=7)
        entry.bind("<Return>", lambda _event: self._search_dtc())
        ttk.Button(toolbar, text="Buscar en base", command=self._search_dtc).pack(side="left")
        self.dtc_count_label = ttk.Label(toolbar, text="", style="Muted.TLabel")
        self.dtc_count_label.pack(side="right")

        columns = ("code", "status", "description", "manufacturer", "type")
        self.dtc_tree = ttk.Treeview(self.tab_dtc, columns=columns, show="headings", selectmode="browse")
        headings = {
            "code": ("Código", 90),
            "status": ("Estado", 110),
            "description": ("Descripción", 600),
            "manufacturer": ("Fabricante", 160),
            "type": ("Tipo", 100),
        }
        for column, (title, width) in headings.items():
            self.dtc_tree.heading(column, text=title)
            self.dtc_tree.column(column, width=width, anchor="w")
        scroll = ttk.Scrollbar(self.tab_dtc, orient="vertical", command=self.dtc_tree.yview)
        self.dtc_tree.configure(yscrollcommand=scroll.set)
        self.dtc_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_live(self) -> None:
        wrapper = ttk.Frame(self.tab_live, style="Panel.TFrame")
        wrapper.pack(fill="both", expand=True)
        left = ttk.Frame(wrapper, style="Panel.TFrame", padding=(0, 0, 12, 0))
        left.pack(side="left", fill="y")
        right = ttk.Frame(wrapper, style="Panel.TFrame")
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(left, text="Sensores seleccionados", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        self.pid_vars: dict[int, tk.BooleanVar] = {}
        defaults = {0x0C, 0x0D, 0x05, 0x42, 0x10, 0x5E}
        for pid, (name, unit) in PID_DEFINITIONS.items():
            var = tk.BooleanVar(value=pid in defaults)
            self.pid_vars[pid] = var
            ttk.Checkbutton(left, text=f"{name} [{unit}] · PID {pid:02X}", variable=var).pack(anchor="w", pady=3)
        ttk.Button(left, text="Iniciar datos", style="Accent.TButton", command=self._start_live).pack(fill="x", pady=(14, 5))
        ttk.Button(left, text="Detener", command=self._stop_live).pack(fill="x")
        self.fuel_source_label = ttk.Label(left, text="Flujómetro: no disponible", style="Muted.TLabel", wraplength=260)
        self.fuel_source_label.pack(anchor="w", pady=15)

        columns = ("parameter", "value", "unit", "pid")
        self.live_tree = ttk.Treeview(right, columns=columns, show="headings")
        for column, title, width in (
            ("parameter", "Parámetro", 330),
            ("value", "Valor actual", 160),
            ("unit", "Unidad", 110),
            ("pid", "PID", 90),
        ):
            self.live_tree.heading(column, text=title)
            self.live_tree.column(column, width=width, anchor="w")
        self.live_tree.pack(fill="both", expand=True)
        self.live_items: dict[int, str] = {}
        for pid, (name, unit) in PID_DEFINITIONS.items():
            item = self.live_tree.insert("", "end", values=(name, "--", unit, f"01{pid:02X}"))
            self.live_items[pid] = item

    def _build_scope(self) -> None:
        toolbar = ttk.Frame(self.tab_scope, style="Panel.TFrame")
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar, text="Señal ECU:", style="Panel.TLabel").pack(side="left")
        self.scope_name_to_pid = {f"{name} [{unit}]": pid for pid, (name, unit) in PID_DEFINITIONS.items()}
        self.scope_var = tk.StringVar(value="RPM [rpm]")
        ttk.Combobox(toolbar, textvariable=self.scope_var, values=list(self.scope_name_to_pid), state="readonly", width=38).pack(side="left", padx=7)
        ttk.Button(toolbar, text="Iniciar", style="Accent.TButton", command=self._start_scope).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Detener", command=self._stop_live).pack(side="left")
        self.scope_rate = ttk.Label(toolbar, text="0 muestras", style="Muted.TLabel")
        self.scope_rate.pack(side="right")
        self.scope_canvas = ScopeCanvas(self.tab_scope, height=540)
        self.scope_canvas.pack(fill="both", expand=True)
        warning = (
            "Este gráfico representa parámetros transmitidos por la ECU mediante OBD-II. No representa la forma de onda eléctrica directa de CKP, CMP, "
            "inyectores, bobinas, CAN o PWM; esas señales requieren un osciloscopio físico y sondas apropiadas."
        )
        ttk.Label(self.tab_scope, text=warning, style="Muted.TLabel", wraplength=1250, justify="left").pack(anchor="w", pady=(8, 0))
        self.scope_samples = 0

    def _build_tests(self) -> None:
        wrapper = ttk.Frame(self.tab_tests, style="Panel.TFrame")
        wrapper.pack(fill="both", expand=True)
        left = ttk.Frame(wrapper, style="Panel.TFrame")
        left.pack(side="left", fill="y", padx=(0, 12))
        right = ttk.Frame(wrapper, style="Panel.TFrame")
        right.pack(side="left", fill="both", expand=True)
        tests = [
            "Verificación de voltaje y carga",
            "Respuesta de RPM y acelerador",
            "Respuesta MAF bajo carga",
            "Temperatura y termostato",
            "Monitores de emisiones",
            "Prueba de ruta controlada",
        ]
        self.test_list = tk.Listbox(left, bg="#101720", fg=TEXT, selectbackground=RED, relief="flat", width=36, height=16, font=("Segoe UI", 10))
        for test in tests:
            self.test_list.insert("end", test)
        self.test_list.pack(fill="y", expand=True)
        self.test_list.bind("<<ListboxSelect>>", self._show_test)
        self.test_text = tk.Text(right, bg="#0D131B", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 10), padx=12, pady=12)
        self.test_text.pack(fill="both", expand=True)
        self.test_list.selection_set(0)
        self._show_test()

    def _build_console(self) -> None:
        toolbar = ttk.Frame(self.tab_console, style="Panel.TFrame")
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar, text="Comando ELM327:", style="Panel.TLabel").pack(side="left")
        self.console_command_var = tk.StringVar(value="ATI")
        entry = ttk.Entry(toolbar, textvariable=self.console_command_var, width=35)
        entry.pack(side="left", padx=7)
        entry.bind("<Return>", lambda _event: self._send_console())
        ttk.Button(toolbar, text="Enviar", style="Accent.TButton", command=self._send_console).pack(side="left")
        ttk.Button(toolbar, text="Limpiar consola", command=lambda: self.console_text.delete("1.0", "end")).pack(side="right")
        self.console_text = tk.Text(self.tab_console, bg="#05080C", fg="#8FFFAE", insertbackground="#8FFFAE", relief="flat", font=("Consolas", 10), padx=10, pady=10)
        self.console_text.pack(fill="both", expand=True)
        self.console_text.insert("end", "AUTOGUARD CONSOLA TÉCNICA\n")

    def _build_report(self) -> None:
        wrapper = ttk.Frame(self.tab_report, style="Panel.TFrame")
        wrapper.pack(fill="both", expand=True)
        form = ttk.Frame(wrapper, style="Panel.TFrame")
        form.pack(side="left", fill="y", padx=(0, 20))
        fields = [
            ("Cliente", "cliente"),
            ("Patente", "patente"),
            ("Marca", "marca"),
            ("Modelo", "modelo"),
            ("Año", "anio"),
            ("VIN", "vin"),
            ("Kilometraje", "kilometraje"),
            ("Motor", "motor"),
        ]
        self.report_vars: dict[str, tk.StringVar] = {}
        for row, (label, key) in enumerate(fields):
            ttk.Label(form, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
            variable = tk.StringVar()
            self.report_vars[key] = variable
            ttk.Entry(form, textvariable=variable, width=38).grid(row=row, column=1, sticky="ew", pady=5)
        ttk.Button(form, text="Generar PDF Premium", style="Accent.TButton", command=self._generate_report).grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(18, 6))
        self.report_status = ttk.Label(form, text="", style="Muted.TLabel", wraplength=420)
        self.report_status.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="w", pady=5)

        notes_frame = ttk.Frame(wrapper, style="Panel.TFrame")
        notes_frame.pack(side="left", fill="both", expand=True)
        ttk.Label(notes_frame, text="Observaciones del técnico", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 7))
        self.report_notes = tk.Text(notes_frame, bg="#0D131B", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", padx=10, pady=10)
        self.report_notes.pack(fill="both", expand=True)

    def _build_info(self) -> None:
        canvas = tk.Canvas(self.tab_info, bg=PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_info, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, style="Panel.TFrame", padding=12)
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(inner, text="INFORMACIÓN Y PLANIFICACIÓN DE LA APLICACIÓN", style="Panel.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 14))
        details = (
            f"Aplicación: {APP_NAME}\n"
            f"Versión: {APP_VERSION}\n"
            f"Compilación: {APP_BUILD}\n"
            f"Autor: {APP_AUTHOR}\n"
            "Estado: instalación limpia · sin licencias, bloqueos ni vencimientos\n"
            f"Base DTC: {self.db_stats['unique_codes']:,} códigos únicos · {self.db_stats['definitions']:,} definiciones · {self.db_stats['manufacturers']} fabricantes"
        ).replace(",", ".")
        ttk.Label(inner, text=details, style="Panel.TLabel", justify="left", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 15))

        sections = [
            (
                "Funciones integradas",
                "• Conexión ELM327 mediante WiFi, puertos COM y simulador.\n"
                "• Detección automática de protocolo OBD-II.\n"
                "• Lectura de DTC confirmados, pendientes y permanentes.\n"
                "• Base offline ampliada con códigos P, B, C y U.\n"
                "• Datos en vivo seleccionables y RPM prioritaria.\n"
                "• Flujómetro PID 015E en L/h con alternativa identificada desde MAF.\n"
                "• Osciloscopio de telemetría ECU en vivo.\n"
                "• Pruebas funcionales guiadas, consola técnica e informe PDF Premium.",
            ),
            (
                "Planificación técnica",
                "1. Validar el funcionamiento completo en modo simulador.\n"
                "2. Confirmar conexión COM y WiFi con diferentes adaptadores ELM327.\n"
                "3. Probar lectura de PID 015E en vehículos compatibles.\n"
                "4. Confirmar estimación MAF en vehículos sin PID 015E.\n"
                "5. Validar DTC genéricos y específicos por marca/VIN.\n"
                "6. Registrar pruebas reales para futuras correcciones aprobadas.",
            ),
            (
                "Criterios de seguridad diagnóstica",
                "No reemplazar componentes únicamente por un código. Confirmar alimentación, masa, conectores, cableado, señal y documentación OEM. "
                "Las pruebas bidireccionales reales dependen del vehículo, protocolo, hardware y autorización del módulo. ELM327 genérico no sustituye un equipo OEM/J2534 ni un osciloscopio físico.",
            ),
        ]
        for title, text in sections:
            box = ttk.Frame(inner, style="Panel.TFrame", padding=10)
            box.pack(fill="x", pady=6)
            ttk.Label(box, text=title, style="Panel.TLabel", font=("Segoe UI", 12, "bold"), foreground=RED).pack(anchor="w", pady=(0, 6))
            ttk.Label(box, text=text, style="Panel.TLabel", justify="left", wraplength=1120).pack(anchor="w")

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, padding=(14, 6))
        bar.pack(fill="x")
        self.status_label = ttk.Label(bar, text="Listo", foreground=MUTED)
        self.status_label.pack(side="left")
        ttk.Label(bar, text=f"Autor: {APP_AUTHOR}", foreground=MUTED).pack(side="right")

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _append_summary(self, text: str) -> None:
        self.session_summary.configure(state="normal")
        self.session_summary.insert("end", text.rstrip() + "\n")
        self.session_summary.see("end")
        self.session_summary.configure(state="disabled")

    def _refresh_ports(self) -> None:
        ports = ELM327Client.available_serial_ports()
        self.com_combo.configure(values=ports)
        if ports and self.com_var.get() not in ports:
            self.com_var.set(ports[0])
        self._set_status(f"Puertos detectados: {', '.join(ports) if ports else 'ninguno'}")

    def _connection_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            mode=self.mode_var.get(),
            serial_port=self.com_var.get().strip(),
            baudrate=int(self.baud_var.get()),
            wifi_host=self.host_var.get().strip(),
            wifi_port=int(self.wifi_port_var.get()),
            timeout=float(self.timeout_var.get()),
        )

    def _connect(self) -> None:
        self.connect_button.configure(state="disabled")
        self._set_status("Conectando...")

        def task() -> None:
            try:
                protocol = self.client.connect(self._connection_config())
                supported = self.client.supported_pids()
                self.ui_events.put(("connected", protocol, supported))
            except Exception as exc:
                self.ui_events.put(("error", "Conexión", str(exc)))
            finally:
                self.ui_events.put(("connect_button", "normal"))

        threading.Thread(target=task, daemon=True).start()

    def _disconnect(self) -> None:
        self._stop_live()
        self.client.disconnect()
        self.connection_indicator.itemconfigure("dot", fill="#59636E")
        self.header_status.configure(text="Sin conexión")
        self.connection_detail.configure(text="Estado: sin conexión")
        self.protocol_label.configure(text="Protocolo: Sin conexión")
        self._set_status("Desconectado")
        self._append_summary("Conexión cerrada.")

    def _scan_dtcs(self) -> None:
        if not self.client.connected:
            messagebox.showwarning("AUTOGUARD", "Conecte primero el adaptador o use el simulador.")
            return
        self._set_status("Escaneando DTC confirmados, pendientes y permanentes...")

        def task() -> None:
            found: list[tuple[str, str]] = []
            for mode, status in (("03", "Confirmado"), ("07", "Pendiente"), ("0A", "Permanente")):
                try:
                    for code in self.client.read_dtcs(mode):
                        if (code, status) not in found:
                            found.append((code, status))
                except Exception as exc:
                    self.ui_events.put(("log", f"DTC modo {mode}: {exc}"))
            self.ui_events.put(("dtcs", found))

        threading.Thread(target=task, daemon=True).start()

    def _clear_dtcs(self) -> None:
        if not self.client.connected:
            messagebox.showwarning("AUTOGUARD", "No existe conexión activa.")
            return
        if not messagebox.askyesno("Borrar DTC", "¿Confirma el borrado de códigos después de guardar la evidencia?"):
            return

        def task() -> None:
            try:
                success = self.client.clear_dtcs()
                self.ui_events.put(("info", "Borrar DTC", "La ECU confirmó el borrado." if success else "La ECU no confirmó el borrado."))
            except Exception as exc:
                self.ui_events.put(("error", "Borrar DTC", str(exc)))

        threading.Thread(target=task, daemon=True).start()

    def _populate_dtc_tree(self, records: list[tuple[DTCRecord, str]]) -> None:
        for item in self.dtc_tree.get_children():
            self.dtc_tree.delete(item)
        self.current_dtcs.clear()
        for record, status in records:
            type_text = "Genérico" if record.is_generic else "Específico"
            self.dtc_tree.insert("", "end", values=(record.code, status, record.description, record.manufacturer, type_text))
            self.current_dtcs.append(
                {
                    "code": record.code,
                    "status": status,
                    "description": record.description,
                    "manufacturer": record.manufacturer,
                }
            )
        self.dtc_count_label.configure(text=f"{len(records)} definiciones mostradas")

    def _search_dtc(self) -> None:
        query = self.dtc_search_var.get().strip()
        if not query:
            return
        records = self.database.search(query, limit=300)
        self._populate_dtc_tree([(record, "Base offline") for record in records])
        self._set_status(f"Búsqueda DTC: {len(records)} resultados")

    def _selected_pids(self) -> list[int]:
        return [pid for pid, variable in self.pid_vars.items() if variable.get()]

    def _restart_worker(self, pids: list[int]) -> None:
        self._stop_live()
        if not self.client.connected:
            raise RuntimeError("No existe conexión activa")
        if not pids:
            raise RuntimeError("Seleccione al menos un PID")
        self.live_worker = LiveDataWorker(self.client, pids, self.data_events)
        self.live_worker.start()
        self._set_status("Datos en vivo activos")

    def _start_live(self) -> None:
        try:
            self._restart_worker(self._selected_pids())
        except Exception as exc:
            messagebox.showwarning("Datos en vivo", str(exc))

    def _start_scope(self) -> None:
        pid = self.scope_name_to_pid.get(self.scope_var.get(), 0x0C)
        name, unit = PID_DEFINITIONS[pid]
        ranges = {0x05: (30, 130), 0x0C: (0, 7000), 0x0D: (0, 240), 0x10: (0, 150), 0x11: (0, 100), 0x42: (8, 18), 0x5E: (0, 60)}
        minimum, maximum = ranges.get(pid, (0, 100))
        self.scope_canvas.configure_signal(name, unit, minimum, maximum)
        self.scope_samples = 0
        pids = list(dict.fromkeys(self._selected_pids() + [pid]))
        try:
            self._restart_worker(pids)
        except Exception as exc:
            messagebox.showwarning("Osciloscopio", str(exc))

    def _stop_live(self) -> None:
        if self.live_worker is not None:
            self.live_worker.stop()
            self.live_worker.join(timeout=1.0)
            self.live_worker = None
        self._set_status("Datos en vivo detenidos")

    def _show_test(self, _event=None) -> None:
        selected = self.test_list.curselection()
        index = selected[0] if selected else 0
        guides = [
            "VERIFICACIÓN DE VOLTAJE Y CARGA\n\n1. Contacto apagado: mida batería en reposo.\n2. Arranque y observe caída de tensión.\n3. Motor en marcha: compare voltaje ECU PID 0142 con multímetro.\n4. Aplique cargas eléctricas y confirme estabilidad.\n\nCriterio: confirme especificaciones del fabricante antes de concluir.",
            "RESPUESTA DE RPM Y ACELERADOR\n\n1. Motor a temperatura de operación.\n2. Registre RPM y posición de acelerador.\n3. Acelere progresivamente sin carga.\n4. Compruebe continuidad, ausencia de saltos y retorno estable.\n\nNo mantenga RPM elevadas innecesariamente.",
            "RESPUESTA MAF BAJO CARGA\n\n1. Revise filtro, ductos y fugas.\n2. Registre MAF en ralentí.\n3. Registre MAF durante aceleración controlada.\n4. Compare tendencia con RPM, MAP y carga calculada.\n\nEl valor esperado depende de cilindrada, turbo y condiciones ambientales.",
            "TEMPERATURA Y TERMOSTATO\n\n1. Inicie con motor frío.\n2. Registre aumento continuo de ECT.\n3. Observe estabilización al abrir el termostato.\n4. Confirme operación del ventilador según diseño.\n\nNo abra el circuito de refrigeración en caliente.",
            "MONITORES DE EMISIONES\n\n1. Lea estado de monitores antes de borrar DTC.\n2. Registre pendientes y permanentes.\n3. Realice ciclo de conducción OEM cuando corresponda.\n4. Reescanee sin borrar evidencia.\n\nUn monitor incompleto no confirma una avería.",
            "PRUEBA DE RUTA CONTROLADA\n\n1. Defina ruta segura y condiciones de prueba.\n2. Use acompañante para operar el computador.\n3. Registre los PID relacionados con la falla.\n4. Marque el momento exacto del síntoma.\n5. Reescanee al finalizar.\n\nNunca opere el computador mientras conduce.",
        ]
        self.test_text.delete("1.0", "end")
        self.test_text.insert("end", guides[index])

    def _send_console(self) -> None:
        command = self.console_command_var.get().strip()
        if not command:
            return
        if not self.client.connected:
            messagebox.showwarning("Consola", "No existe conexión activa.")
            return

        def task() -> None:
            try:
                response = self.client.command(command)
                self.ui_events.put(("console", f"> {command}\n{response}\n"))
            except Exception as exc:
                self.ui_events.put(("error", "Consola", str(exc)))

        threading.Thread(target=task, daemon=True).start()

    def _generate_report(self) -> None:
        output = Path(filedialog.asksaveasfilename(
            title="Guardar informe AUTOGUARD",
            defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")],
            initialfile=default_report_path().name,
            initialdir=str(default_report_path().parent),
        ))
        if not str(output):
            return
        vehicle = {key: variable.get() for key, variable in self.report_vars.items()}
        live: dict[str, str] = {}
        for pid, value in self.latest_values.items():
            if pid in PID_DEFINITIONS:
                name, unit = PID_DEFINITIONS[pid]
                live[name] = f"{value:.2f} {unit}"
        live["Origen flujómetro"] = self.fuel_source
        try:
            generate_pdf_report(
                output,
                vehicle=vehicle,
                protocol=self.client.protocol,
                dtcs=self.current_dtcs,
                live_values=live,
                notes=self.report_notes.get("1.0", "end").strip(),
                author=APP_AUTHOR,
                version=APP_VERSION,
            )
            self.report_status.configure(text=f"Informe creado: {output}")
            if messagebox.askyesno("Informe creado", "El informe se creó correctamente. ¿Desea abrirlo?"):
                open_path(output)
        except Exception as exc:
            messagebox.showerror("Informe PDF", str(exc))

    def _drain_queues(self) -> None:
        while True:
            try:
                event = self.ui_events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "log":
                self.console_text.insert("end", str(event[1]).rstrip() + "\n")
                self.console_text.see("end")
            elif kind == "connected":
                protocol, supported = event[1], event[2]
                self.supported_pids = set(supported)
                self.connection_indicator.itemconfigure("dot", fill=GREEN)
                self.header_status.configure(text="Conectado")
                self.connection_detail.configure(text=f"Estado: conectado · {protocol}")
                self.protocol_label.configure(text=f"Protocolo: {protocol}")
                self._set_status(f"Conectado · {len(supported)} PID anunciados por la ECU")
                self._append_summary(f"Conexión establecida: {protocol}")
            elif kind == "connect_button":
                self.connect_button.configure(state=event[1])
            elif kind == "error":
                self._set_status(f"Error: {event[2]}")
                messagebox.showerror(event[1], event[2])
            elif kind == "info":
                messagebox.showinfo(event[1], event[2])
            elif kind == "console":
                self.console_text.insert("end", event[1])
                self.console_text.see("end")
            elif kind == "dtcs":
                found: list[tuple[str, str]] = event[1]
                rows: list[tuple[DTCRecord, str]] = []
                for code, status in found:
                    records = self.database.lookup(code)
                    if records:
                        rows.extend((record, status) for record in records)
                    else:
                        rows.append((DTCRecord(code, "Descripción no disponible en la base", "No identificado", True, ""), status))
                self._populate_dtc_tree(rows)
                self._set_status(f"Escaneo finalizado: {len(found)} códigos únicos")
                self._append_summary(f"Escaneo DTC: {len(found)} códigos únicos.")

        while True:
            try:
                packet = self.data_events.get_nowait()
            except queue.Empty:
                break
            self.latest_values.update(packet.get("values", {}))
            self.fuel_source = packet.get("fuel_source", "No disponible")
            self.fuel_source_label.configure(text=f"Flujómetro: {self.fuel_source}")
            for pid, value in packet.get("values", {}).items():
                if pid in self.live_items:
                    name, unit = PID_DEFINITIONS[pid]
                    self.live_tree.item(self.live_items[pid], values=(name, f"{value:.2f}", unit, f"01{pid:02X}"))
            self.gauge_rpm.set_value(self.latest_values.get(0x0C, 0), 0x0C in packet.get("values", {}))
            self.gauge_speed.set_value(self.latest_values.get(0x0D, 0), 0x0D in packet.get("values", {}))
            self.gauge_temp.set_value(self.latest_values.get(0x05, 40), 0x05 in packet.get("values", {}))
            self.gauge_voltage.set_value(self.latest_values.get(0x42, 8), 0x42 in packet.get("values", {}))
            scope_pid = self.scope_name_to_pid.get(self.scope_var.get(), 0x0C)
            if scope_pid in packet.get("values", {}):
                self.scope_canvas.add_sample(packet["values"][scope_pid])
                self.scope_samples += 1
                self.scope_rate.configure(text=f"{self.scope_samples} muestras")
            for error in packet.get("errors", []):
                self.console_text.insert("end", f"[PID] {error}\n")
        self.after(80, self._drain_queues)

    def _on_close(self) -> None:
        self._stop_live()
        self.client.disconnect()
        self.destroy()


def main() -> None:
    try:
        app = AutoguardApp()
        app.mainloop()
    except Exception as exc:
        log_dir = Path.home() / "AppData" / "Local" / "Autoguard" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "AUTOGUARD_INICIO_ERROR.log"
        log_file.write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{type(exc).__name__}: {exc}\n", encoding="utf-8")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("AUTOGUARD SCAN DIOS", f"No fue posible iniciar la aplicación.\n\n{exc}\n\nRegistro: {log_file}")
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
