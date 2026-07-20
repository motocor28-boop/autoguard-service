from __future__ import annotations

import logging
import os
import queue
import threading
import time
import tkinter as tk
from collections import defaultdict, deque
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .config import (
    APP_NAME,
    APP_VERSION,
    COLORS,
    LIVE_PID_ORDER,
    LOG_FILE,
    PID_DEFINITIONS,
    REPORT_DIR,
)
from .dtc_database import DTCDatabase, TOTAL_DTC_RECORDS
from .obd import (
    DTCResult,
    ELM327Client,
    VehicleScan,
    available_serial_ports,
    create_client,
)
from .reporting import generate_pdf_report


class SuperScanApp(tk.Tk):
    def __init__(self, logger: logging.Logger):
        super().__init__()
        self.logger = logger
        self.db = DTCDatabase()
        self.client: ELM327Client | None = None
        self.scan_result: VehicleScan | None = None
        self.current_dtcs: list[DTCResult] = []
        self.current_live: dict[str, tuple[float | None, str]] = {}
        self.history: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=300))
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.live_running = False
        self.live_busy = False
        self.connected_at: float | None = None
        self._closing = False

        self.title(APP_NAME)
        self.minsize(1100, 700)
        self.geometry("1440x900")
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        self.configure(bg=COLORS["surface_alt"])
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._configure_styles()
        self._build_shell()
        self._build_pages()
        self.show_page("Resumen")
        self.after(100, self._process_events)
        self.after(1000, self._live_tick)
        self.logger.info("Inicio %s", APP_NAME)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=COLORS["surface"])
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("Alt.TFrame", background=COLORS["surface_alt"])
        style.configure("TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), foreground=COLORS["nav"])
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=COLORS["muted"])
        style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 11), foreground=COLORS["nav"])
        style.configure("Metric.TLabel", font=("Segoe UI Semibold", 24), foreground=COLORS["primary"])
        style.configure("OrangeMetric.TLabel", font=("Segoe UI Semibold", 24), foreground=COLORS["accent"])
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.configure("Primary.TButton", background=COLORS["primary"], foreground="white")
        style.map("Primary.TButton", background=[("active", COLORS["primary_dark"]), ("disabled", "#9BBBD5")])
        style.configure("Danger.TButton", background=COLORS["danger"], foreground="white")
        style.map("Danger.TButton", background=[("active", "#B92E2E")])
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=28, background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background=COLORS["nav"], foreground="white")
        style.map("Treeview.Heading", background=[("active", COLORS["nav_hover"])])
        style.configure("TNotebook.Tab", padding=(12, 7))

    def _build_shell(self) -> None:
        self.sidebar = tk.Frame(self, bg=COLORS["nav"], width=225)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=COLORS["nav"], height=108)
        brand.pack(fill="x", padx=14, pady=(12, 8))
        brand.pack_propagate(False)
        tk.Label(brand, text="AUTOGUARD", bg=COLORS["nav"], fg=COLORS["accent"], font=("Segoe UI Black", 20)).pack(anchor="w", pady=(12, 0))
        tk.Label(brand, text="SUPERSCAN 2.0", bg=COLORS["nav"], fg="white", font=("Segoe UI Semibold", 13)).pack(anchor="w")
        tk.Label(brand, text="Diagnóstico automotriz multimarca", bg=COLORS["nav"], fg="#A9BED2", font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

        nav_items = [
            "Resumen", "Conexión", "Escaneo", "Códigos DTC", "Datos en vivo",
            "Gráficos", "Freeze Frame", "Monitores", "Base DTC", "Informe", "Consola",
        ]
        for name in nav_items:
            button = tk.Button(
                self.sidebar,
                text=name,
                anchor="w",
                relief="flat",
                bd=0,
                padx=20,
                pady=9,
                bg=COLORS["nav"],
                fg="#DCE7F0",
                activebackground=COLORS["nav_hover"],
                activeforeground="white",
                font=("Segoe UI Semibold", 10),
                command=lambda n=name: self.show_page(n),
                cursor="hand2",
            )
            button.pack(fill="x", padx=8, pady=1)
            self.nav_buttons[name] = button

        footer = tk.Frame(self.sidebar, bg=COLORS["nav"])
        footer.pack(side="bottom", fill="x", padx=14, pady=14)
        self.sidebar_status = tk.Label(footer, text="● DESCONECTADO", bg=COLORS["nav"], fg="#FF7B7B", font=("Segoe UI Semibold", 9))
        self.sidebar_status.pack(anchor="w")
        tk.Label(footer, text=f"Versión {APP_VERSION}", bg=COLORS["nav"], fg="#7791A8", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        self.main = tk.Frame(self, bg=COLORS["surface_alt"])
        self.main.pack(side="left", fill="both", expand=True)

        self.topbar = tk.Frame(self.main, bg="white", height=66, highlightbackground=COLORS["border"], highlightthickness=1)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)
        self.page_title = tk.Label(self.topbar, text="Resumen", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 18))
        self.page_title.pack(side="left", padx=24)
        self.status_text = tk.Label(self.topbar, text="Aplicación lista", bg="white", fg=COLORS["muted"], font=("Segoe UI", 9))
        self.status_text.pack(side="right", padx=(8, 22))
        self.status_dot = tk.Label(self.topbar, text="●", bg="white", fg=COLORS["danger"], font=("Segoe UI", 13))
        self.status_dot.pack(side="right")

        self.content = tk.Frame(self.main, bg=COLORS["surface_alt"])
        self.content.pack(fill="both", expand=True, padx=20, pady=18)

    def _build_pages(self) -> None:
        self._build_summary_page()
        self._build_connection_page()
        self._build_scan_page()
        self._build_dtc_page()
        self._build_live_page()
        self._build_graph_page()
        self._build_freeze_page()
        self._build_monitors_page()
        self._build_database_page()
        self._build_report_page()
        self._build_console_page()

    def _new_page(self, name: str) -> tk.Frame:
        frame = tk.Frame(self.content, bg=COLORS["surface_alt"])
        self.pages[name] = frame
        return frame

    def _card(self, parent, *, padding: int = 16) -> tk.Frame:
        card = tk.Frame(parent, bg="white", highlightbackground=COLORS["border"], highlightthickness=1)
        inner = tk.Frame(card, bg="white")
        inner.pack(fill="both", expand=True, padx=padding, pady=padding)
        card.inner = inner  # type: ignore[attr-defined]
        return card

    def _section_header(self, parent, title: str, subtitle: str = "") -> None:
        tk.Label(parent, text=title, bg=COLORS["surface_alt"], fg=COLORS["nav"], font=("Segoe UI Semibold", 21)).pack(anchor="w")
        if subtitle:
            tk.Label(parent, text=subtitle, bg=COLORS["surface_alt"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 14))

    def _build_summary_page(self) -> None:
        page = self._new_page("Resumen")
        self._section_header(page, "Resumen del diagnóstico", "Estado general del vehículo, conexión y parámetros críticos")

        top = tk.Frame(page, bg=COLORS["surface_alt"])
        top.pack(fill="x")
        top.columnconfigure(0, weight=3)
        top.columnconfigure(1, weight=2)

        vehicle = self._card(top)
        vehicle.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        health = self._card(top)
        health.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(vehicle.inner, text="VEHÍCULO / ECU", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 12)).pack(anchor="w")
        self.vehicle_subtitle = tk.Label(vehicle.inner, text="Esperando conexión y lectura de identificación", bg="white", fg=COLORS["muted"], font=("Segoe UI", 9))
        self.vehicle_subtitle.pack(anchor="w")
        self.logo_canvas = tk.Canvas(vehicle.inner, height=230, bg="white", highlightthickness=0)
        self.logo_canvas.pack(fill="x", pady=(4, 2))
        self.logo_canvas.bind("<Configure>", lambda _e: self._draw_autoguard_logo())
        self.summary_vin = tk.Label(vehicle.inner, text="VIN: —", bg="white", fg=COLORS["text"], font=("Consolas", 10))
        self.summary_vin.pack(anchor="w")
        self.summary_protocol = tk.Label(vehicle.inner, text="Protocolo: —", bg="white", fg=COLORS["muted"], font=("Segoe UI", 9))
        self.summary_protocol.pack(anchor="w", pady=(3, 0))

        tk.Label(health.inner, text="ESTADO DEL DIAGNÓSTICO", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 12)).pack(anchor="w")
        self.health_indicator = tk.Canvas(health.inner, width=160, height=160, bg="white", highlightthickness=0)
        self.health_indicator.pack(pady=12)
        self.health_indicator.create_oval(12, 12, 148, 148, width=12, outline=COLORS["border"])
        self.health_arc = self.health_indicator.create_arc(12, 12, 148, 148, start=90, extent=0, style="arc", width=12, outline=COLORS["success"])
        self.health_text = self.health_indicator.create_text(80, 72, text="—", font=("Segoe UI Semibold", 27), fill=COLORS["nav"])
        self.health_label = self.health_indicator.create_text(80, 104, text="Sin escaneo", font=("Segoe UI", 9), fill=COLORS["muted"])
        self.summary_dtc_count = tk.Label(health.inner, text="Códigos DTC: —", bg="white", fg=COLORS["text"], font=("Segoe UI Semibold", 11))
        self.summary_dtc_count.pack()
        self.summary_pid_count = tk.Label(health.inner, text="PIDs disponibles: —", bg="white", fg=COLORS["muted"], font=("Segoe UI", 9))
        self.summary_pid_count.pack(pady=(3, 0))

        metrics = tk.Frame(page, bg=COLORS["surface_alt"])
        metrics.pack(fill="x", pady=(16, 0))
        for col in range(4):
            metrics.columnconfigure(col, weight=1)

        self.metric_widgets: dict[str, tk.Label] = {}
        metric_specs = [
            ("RPM motor", "rpm", "Metric.TLabel"),
            ("Voltaje adaptador", "V", "Metric.TLabel"),
            ("Caudal de combustible", "L/h", "OrangeMetric.TLabel"),
            ("Nivel de combustible", "%", "OrangeMetric.TLabel"),
        ]
        for col, (name, unit, style_name) in enumerate(metric_specs):
            card = self._card(metrics, padding=14)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0 if col == 3 else 6))
            tk.Label(card.inner, text=name.upper(), bg="white", fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w")
            value = ttk.Label(card.inner, text="—", style=style_name)
            value.pack(anchor="w", pady=(5, 0))
            tk.Label(card.inner, text=unit, bg="white", fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")
            self.metric_widgets[name] = value

        bottom = self._card(page)
        bottom.pack(fill="both", expand=True, pady=(16, 0))
        tk.Label(bottom.inner, text="ACCIONES RÁPIDAS", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 11)).pack(anchor="w")
        actions = tk.Frame(bottom.inner, bg="white")
        actions.pack(anchor="w", pady=(10, 0))
        ttk.Button(actions, text="Conectar", style="Primary.TButton", command=lambda: self.show_page("Conexión")).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Escaneo completo", command=self.start_scan).pack(side="left", padx=8)
        ttk.Button(actions, text="Leer DTC", command=self.refresh_dtcs).pack(side="left", padx=8)
        ttk.Button(actions, text="Generar informe", command=self.generate_report).pack(side="left", padx=8)

    def _draw_autoguard_logo(self) -> None:
        canvas = self.logo_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 500)
        cx = width / 2
        cy = 112
        scale = min(width / 760.0, 1.15)
        orange = COLORS["accent"]
        dark = COLORS["nav"]
        points = [
            (cx - 140 * scale, cy - 70 * scale), (cx + 110 * scale, cy - 70 * scale),
            (cx + 145 * scale, cy - 35 * scale), (cx + 175 * scale, cy - 35 * scale),
            (cx + 175 * scale, cy + 50 * scale), (cx + 135 * scale, cy + 50 * scale),
            (cx + 110 * scale, cy + 78 * scale), (cx - 125 * scale, cy + 78 * scale),
            (cx - 150 * scale, cy + 50 * scale), (cx - 185 * scale, cy + 50 * scale),
            (cx - 185 * scale, cy - 25 * scale), (cx - 150 * scale, cy - 25 * scale),
        ]
        flat = [coord for point in points for coord in point]
        canvas.create_polygon(*flat, fill=dark, outline=orange, width=6, joinstyle="round")
        canvas.create_rectangle(cx - 58 * scale, cy - 98 * scale, cx + 42 * scale, cy - 70 * scale, fill=dark, outline=orange, width=5)
        canvas.create_text(cx, cy - 8 * scale, text="A", fill=orange, font=("Segoe UI Black", max(42, int(62 * scale))))
        canvas.create_text(cx, cy + 38 * scale, text="AUTOGUARD", fill=orange, font=("Segoe UI Black", max(17, int(24 * scale))))
        canvas.create_text(cx, cy + 64 * scale, text="SUPERSCAN 2.0", fill="white", font=("Segoe UI Semibold", max(10, int(13 * scale))))

    def _build_connection_page(self) -> None:
        page = self._new_page("Conexión")
        self._section_header(page, "Conexión OBD-II", "Conecte por puerto COM, adaptador Wi-Fi o utilice el simulador integrado")
        card = self._card(page)
        card.pack(fill="x")
        form = card.inner
        form.columnconfigure(1, weight=1)

        tk.Label(form, text="Modo de conexión", bg="white", fg=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        self.connection_mode = ttk.Combobox(form, values=["Simulador", "COM", "WiFi"], state="readonly")
        self.connection_mode.set("Simulador")
        self.connection_mode.grid(row=0, column=1, sticky="ew", pady=6)
        self.connection_mode.bind("<<ComboboxSelected>>", lambda _e: self._update_connection_fields())

        tk.Label(form, text="Puerto COM", bg="white").grid(row=1, column=0, sticky="w", pady=6)
        port_row = tk.Frame(form, bg="white")
        port_row.grid(row=1, column=1, sticky="ew", pady=6)
        port_row.columnconfigure(0, weight=1)
        self.com_port = ttk.Combobox(port_row, values=available_serial_ports(), state="readonly")
        self.com_port.grid(row=0, column=0, sticky="ew")
        ttk.Button(port_row, text="Actualizar", command=self.refresh_ports).grid(row=0, column=1, padx=(8, 0))

        tk.Label(form, text="Velocidad", bg="white").grid(row=2, column=0, sticky="w", pady=6)
        self.baudrate = ttk.Combobox(form, values=[9600, 38400, 57600, 115200], state="readonly")
        self.baudrate.set("38400")
        self.baudrate.grid(row=2, column=1, sticky="ew", pady=6)

        tk.Label(form, text="Dirección Wi-Fi", bg="white").grid(row=3, column=0, sticky="w", pady=6)
        wifi_row = tk.Frame(form, bg="white")
        wifi_row.grid(row=3, column=1, sticky="ew", pady=6)
        wifi_row.columnconfigure(0, weight=1)
        self.wifi_host = ttk.Entry(wifi_row)
        self.wifi_host.insert(0, "192.168.0.10")
        self.wifi_host.grid(row=0, column=0, sticky="ew")
        self.wifi_port = ttk.Entry(wifi_row, width=10)
        self.wifi_port.insert(0, "35000")
        self.wifi_port.grid(row=0, column=1, padx=(8, 0))

        controls = tk.Frame(form, bg="white")
        controls.grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 4))
        self.connect_button = ttk.Button(controls, text="Conectar y detectar protocolo", style="Primary.TButton", command=self.connect_selected)
        self.connect_button.pack(side="left")
        self.disconnect_button = ttk.Button(controls, text="Desconectar", command=self.disconnect, state="disabled")
        self.disconnect_button.pack(side="left", padx=(10, 0))

        info = self._card(page)
        info.pack(fill="both", expand=True, pady=(14, 0))
        tk.Label(info.inner, text="ESTADO DE COMUNICACIÓN", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 11)).pack(anchor="w")
        self.connection_info = tk.Text(info.inner, height=12, wrap="word", bg=COLORS["surface_alt"], fg=COLORS["text"], relief="flat", font=("Consolas", 9), padx=10, pady=10)
        self.connection_info.pack(fill="both", expand=True, pady=(8, 0))
        self.connection_info.insert("end", "Seleccione un modo y presione Conectar.\n")
        self.connection_info.configure(state="disabled")
        self._update_connection_fields()

    def _update_connection_fields(self) -> None:
        mode = self.connection_mode.get()
        self.com_port.configure(state="readonly" if mode == "COM" else "disabled")
        self.baudrate.configure(state="readonly" if mode == "COM" else "disabled")
        wifi_state = "normal" if mode == "WiFi" else "disabled"
        self.wifi_host.configure(state=wifi_state)
        self.wifi_port.configure(state=wifi_state)

    def _build_scan_page(self) -> None:
        page = self._new_page("Escaneo")
        self._section_header(page, "Escaneo automático", "Identificación, protocolo, PIDs soportados, monitores y códigos de falla")
        card = self._card(page)
        card.pack(fill="x")
        controls = tk.Frame(card.inner, bg="white")
        controls.pack(fill="x")
        self.scan_button = ttk.Button(controls, text="Iniciar escaneo completo", style="Primary.TButton", command=self.start_scan)
        self.scan_button.pack(side="left")
        self.scan_progress = ttk.Progressbar(controls, mode="indeterminate", length=240)
        self.scan_progress.pack(side="left", padx=16)
        self.scan_state = tk.Label(controls, text="En espera", bg="white", fg=COLORS["muted"])
        self.scan_state.pack(side="left")

        result = self._card(page)
        result.pack(fill="both", expand=True, pady=(14, 0))
        self.scan_text = tk.Text(result.inner, wrap="word", bg="white", fg=COLORS["text"], relief="flat", font=("Consolas", 10), padx=8, pady=8)
        self.scan_text.pack(fill="both", expand=True)
        self.scan_text.insert("end", "Conecte un adaptador y ejecute el escaneo.\n")
        self.scan_text.configure(state="disabled")

    def _build_dtc_page(self) -> None:
        page = self._new_page("Códigos DTC")
        self._section_header(page, "Códigos DTC", "Códigos confirmados, pendientes y permanentes con descripción offline")
        bar = tk.Frame(page, bg=COLORS["surface_alt"])
        bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="Leer códigos", style="Primary.TButton", command=self.refresh_dtcs).pack(side="left")
        ttk.Button(bar, text="Borrar códigos", style="Danger.TButton", command=self.clear_dtcs).pack(side="left", padx=(8, 0))
        self.dtc_summary_label = tk.Label(bar, text="Sin lectura", bg=COLORS["surface_alt"], fg=COLORS["muted"])
        self.dtc_summary_label.pack(side="right")

        card = self._card(page, padding=8)
        card.pack(fill="both", expand=True)
        columns = ("code", "status", "system", "description")
        self.dtc_tree = ttk.Treeview(card.inner, columns=columns, show="headings")
        self.dtc_tree.heading("code", text="Código")
        self.dtc_tree.heading("status", text="Estado")
        self.dtc_tree.heading("system", text="Sistema")
        self.dtc_tree.heading("description", text="Descripción")
        self.dtc_tree.column("code", width=85, anchor="center", stretch=False)
        self.dtc_tree.column("status", width=170, stretch=False)
        self.dtc_tree.column("system", width=130, stretch=False)
        self.dtc_tree.column("description", width=700)
        scroll = ttk.Scrollbar(card.inner, orient="vertical", command=self.dtc_tree.yview)
        self.dtc_tree.configure(yscrollcommand=scroll.set)
        self.dtc_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_live_page(self) -> None:
        page = self._new_page("Datos en vivo")
        self._section_header(page, "Datos en vivo", "Lectura continua de sensores y parámetros OBD-II")
        bar = tk.Frame(page, bg=COLORS["surface_alt"])
        bar.pack(fill="x", pady=(0, 10))
        self.live_toggle_button = ttk.Button(bar, text="Iniciar actualización", style="Primary.TButton", command=self.toggle_live)
        self.live_toggle_button.pack(side="left")
        self.live_status_label = tk.Label(bar, text="Detenido", bg=COLORS["surface_alt"], fg=COLORS["muted"])
        self.live_status_label.pack(side="left", padx=12)

        card = self._card(page, padding=8)
        card.pack(fill="both", expand=True)
        self.live_tree = ttk.Treeview(card.inner, columns=("name", "value", "unit", "state"), show="headings")
        for col, text, width in (("name", "Parámetro", 350), ("value", "Valor", 160), ("unit", "Unidad", 120), ("state", "Estado", 160)):
            self.live_tree.heading(col, text=text)
            self.live_tree.column(col, width=width, anchor="center" if col != "name" else "w")
        self.live_tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(card.inner, orient="vertical", command=self.live_tree.yview)
        scroll.pack(side="right", fill="y")
        self.live_tree.configure(yscrollcommand=scroll.set)

    def _build_graph_page(self) -> None:
        page = self._new_page("Gráficos")
        self._section_header(page, "Gráficos técnicos HD", "Tendencia temporal de parámetros seleccionados")
        bar = tk.Frame(page, bg=COLORS["surface_alt"])
        bar.pack(fill="x", pady=(0, 10))
        tk.Label(bar, text="Parámetro", bg=COLORS["surface_alt"], fg=COLORS["text"]).pack(side="left")
        names = [PID_DEFINITIONS[cmd][0] for cmd in LIVE_PID_ORDER] + ["Voltaje adaptador"]
        self.graph_parameter = ttk.Combobox(bar, values=names, state="readonly", width=38)
        self.graph_parameter.set("RPM motor")
        self.graph_parameter.pack(side="left", padx=8)
        ttk.Button(bar, text="Actualizar gráfico", command=self.update_graph).pack(side="left")
        ttk.Button(bar, text="Limpiar historial", command=self.clear_graph_history).pack(side="left", padx=(8, 0))

        card = self._card(page, padding=8)
        card.pack(fill="both", expand=True)
        self.figure = Figure(figsize=(10, 5.5), dpi=110, facecolor="white")
        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True, alpha=0.25)
        self.axes.set_title("RPM motor")
        self.axes.set_xlabel("Tiempo de sesión (s)")
        self.graph_canvas = FigureCanvasTkAgg(self.figure, master=card.inner)
        self.graph_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_freeze_page(self) -> None:
        page = self._new_page("Freeze Frame")
        self._section_header(page, "Freeze Frame", "Condiciones almacenadas por la ECU cuando se registró la falla")
        ttk.Button(page, text="Leer Freeze Frame", style="Primary.TButton", command=self.read_freeze_frame).pack(anchor="w", pady=(0, 10))
        card = self._card(page, padding=8)
        card.pack(fill="both", expand=True)
        self.freeze_tree = ttk.Treeview(card.inner, columns=("parameter", "value", "unit"), show="headings")
        self.freeze_tree.heading("parameter", text="Parámetro")
        self.freeze_tree.heading("value", text="Valor")
        self.freeze_tree.heading("unit", text="Unidad")
        self.freeze_tree.column("parameter", width=350)
        self.freeze_tree.column("value", width=260, anchor="center")
        self.freeze_tree.column("unit", width=150, anchor="center")
        self.freeze_tree.pack(fill="both", expand=True)

    def _build_monitors_page(self) -> None:
        page = self._new_page("Monitores")
        self._section_header(page, "Monitores OBD-II", "Estado MIL, cantidad de códigos y disponibilidad de monitores continuos")
        ttk.Button(page, text="Actualizar monitores", style="Primary.TButton", command=self.read_monitors).pack(anchor="w", pady=(0, 10))
        card = self._card(page)
        card.pack(fill="both", expand=True)
        self.monitor_labels: dict[str, tk.Label] = {}
        for key, title in (("mil", "Luz MIL"), ("dtc_count", "Cantidad DTC"), ("misfire_available", "Monitor de fallas de encendido"), ("fuel_available", "Monitor del sistema de combustible"), ("components_available", "Monitor de componentes"), ("raw", "Respuesta cruda PID 0101")):
            row = tk.Frame(card.inner, bg="white")
            row.pack(fill="x", pady=6)
            tk.Label(row, text=title, width=38, anchor="w", bg="white", fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="left")
            label = tk.Label(row, text="—", anchor="w", bg="white", fg=COLORS["muted"], font=("Segoe UI", 10))
            label.pack(side="left", fill="x", expand=True)
            self.monitor_labels[key] = label

    def _build_database_page(self) -> None:
        page = self._new_page("Base DTC")
        self._section_header(page, "Base offline de códigos DTC", f"Catálogo local con {TOTAL_DTC_RECORDS:,} registros propios y genéricos".replace(",", "."))
        search_bar = tk.Frame(page, bg=COLORS["surface_alt"])
        search_bar.pack(fill="x", pady=(0, 10))
        self.db_search_entry = ttk.Entry(search_bar)
        self.db_search_entry.pack(side="left", fill="x", expand=True)
        self.db_search_entry.bind("<Return>", lambda _e: self.search_database())
        ttk.Button(search_bar, text="Buscar", style="Primary.TButton", command=self.search_database).pack(side="left", padx=(8, 0))
        self.db_count_label = tk.Label(search_bar, text=f"{self.db.count():,} códigos".replace(",", "."), bg=COLORS["surface_alt"], fg=COLORS["muted"])
        self.db_count_label.pack(side="right", padx=12)

        card = self._card(page, padding=8)
        card.pack(fill="both", expand=True)
        self.db_tree = ttk.Treeview(card.inner, columns=("code", "system", "scope", "description"), show="headings")
        for col, title, width in (("code", "Código", 85), ("system", "Sistema", 140), ("scope", "Alcance", 110), ("description", "Descripción", 720)):
            self.db_tree.heading(col, text=title)
            self.db_tree.column(col, width=width, anchor="center" if col != "description" else "w")
        self.db_tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(card.inner, orient="vertical", command=self.db_tree.yview)
        scroll.pack(side="right", fill="y")
        self.db_tree.configure(yscrollcommand=scroll.set)
        self.search_database()

    def _build_report_page(self) -> None:
        page = self._new_page("Informe")
        self._section_header(page, "Informe PDF Premium", "Genere un respaldo técnico con identificación, DTC y datos en vivo")
        card = self._card(page)
        card.pack(fill="x")
        tk.Label(card.inner, text="El informe se guardará en:", bg="white", fg=COLORS["text"], font=("Segoe UI Semibold", 11)).pack(anchor="w")
        tk.Label(card.inner, text=str(REPORT_DIR), bg="white", fg=COLORS["muted"], font=("Consolas", 9)).pack(anchor="w", pady=(4, 14))
        buttons = tk.Frame(card.inner, bg="white")
        buttons.pack(anchor="w")
        ttk.Button(buttons, text="Generar informe PDF", style="Primary.TButton", command=self.generate_report).pack(side="left")
        ttk.Button(buttons, text="Abrir carpeta de informes", command=self.open_report_folder).pack(side="left", padx=(8, 0))
        self.report_status = tk.Label(card.inner, text="", bg="white", fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=900, justify="left")
        self.report_status.pack(anchor="w", pady=(14, 0))

    def _build_console_page(self) -> None:
        page = self._new_page("Consola")
        self._section_header(page, "Consola técnica", "Comandos TX/RX y eventos de la sesión")
        bar = tk.Frame(page, bg=COLORS["surface_alt"])
        bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="Limpiar consola", command=self.clear_console).pack(side="left")
        ttk.Button(bar, text="Abrir registro", command=self.open_log).pack(side="left", padx=(8, 0))
        self.console = tk.Text(page, bg=COLORS["console"], fg="#D8E6F3", insertbackground="white", font=("Consolas", 9), relief="flat", padx=12, pady=12)
        self.console.pack(fill="both", expand=True)
        self.console.insert("end", f"{APP_NAME} — consola de comunicación\n")
        self.console.configure(state="disabled")

    def show_page(self, name: str) -> None:
        for page in self.pages.values():
            page.pack_forget()
        page = self.pages[name]
        page.pack(fill="both", expand=True)
        self.page_title.configure(text=name)
        for item, button in self.nav_buttons.items():
            button.configure(bg=COLORS["nav_hover"] if item == name else COLORS["nav"], fg="white" if item == name else "#DCE7F0")
        if name == "Gráficos":
            self.update_graph()

    def _post(self, event: str, payload: object = None) -> None:
        self.events.put((event, payload))

    def _run_worker(self, target: Callable[[], object], success_event: str, *, error_event: str = "error") -> None:
        def worker() -> None:
            try:
                result = target()
                self._post(success_event, result)
            except Exception as exc:
                self.logger.exception("Error en operación %s", success_event)
                self._post(error_event, exc)

        threading.Thread(target=worker, daemon=True).start()

    def _process_events(self) -> None:
        if self._closing:
            return
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "console":
                    self._append_console(str(payload))
                elif event == "connected":
                    self._on_connected(payload)
                elif event == "scan_complete":
                    self._on_scan_complete(payload)
                elif event == "dtcs":
                    self._on_dtcs(payload)
                elif event == "dtcs_cleared":
                    self._on_dtcs_cleared(bool(payload))
                elif event == "live":
                    self._on_live_data(payload)
                elif event == "freeze":
                    self._on_freeze(payload)
                elif event == "monitors":
                    self._on_monitors(payload)
                elif event == "report":
                    self._on_report(payload)
                elif event == "error":
                    self._on_error(payload)
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _append_console(self, text: str) -> None:
        if not hasattr(self, "console"):
            return
        self.console.configure(state="normal")
        self.console.insert("end", text.rstrip() + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def _set_status(self, text: str, connected: bool | None = None) -> None:
        self.status_text.configure(text=text)
        if connected is not None:
            color = COLORS["success"] if connected else COLORS["danger"]
            self.status_dot.configure(fg=color)
            self.sidebar_status.configure(text="● CONECTADO" if connected else "● DESCONECTADO", fg=color if connected else "#FF7B7B")

    def _set_text_widget(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def refresh_ports(self) -> None:
        ports = available_serial_ports()
        self.com_port.configure(values=ports)
        if ports:
            self.com_port.set(ports[0])
        else:
            self.com_port.set("")
        self._set_status(f"Puertos detectados: {len(ports)}")

    def connect_selected(self) -> None:
        if self.client and self.client.connected:
            messagebox.showinfo(APP_NAME, "La aplicación ya está conectada.")
            return
        mode = self.connection_mode.get()
        try:
            wifi_port = int(self.wifi_port.get() or "35000")
            baudrate = int(self.baudrate.get() or "38400")
        except ValueError:
            messagebox.showerror(APP_NAME, "La velocidad o el puerto Wi-Fi no son válidos.")
            return
        self.connect_button.configure(state="disabled")
        self._set_status("Conectando y detectando protocolo...")
        self._write_connection_info("Iniciando adaptador ELM327...\n")

        def operation() -> ELM327Client:
            client = create_client(
                mode,
                self.logger,
                lambda line: self._post("console", line),
                serial_port=self.com_port.get(),
                baudrate=baudrate,
                wifi_host=self.wifi_host.get().strip(),
                wifi_port=wifi_port,
            )
            client.connect()
            return client

        self._run_worker(operation, "connected")

    def _write_connection_info(self, text: str) -> None:
        self.connection_info.configure(state="normal")
        self.connection_info.insert("end", text)
        self.connection_info.see("end")
        self.connection_info.configure(state="disabled")

    def _on_connected(self, payload: object) -> None:
        self.client = payload if isinstance(payload, ELM327Client) else None
        if not self.client:
            self._on_error(RuntimeError("Cliente OBD no disponible"))
            return
        self.connected_at = time.monotonic()
        self.connect_button.configure(state="disabled")
        self.disconnect_button.configure(state="normal")
        self._set_status(f"Conectado: {self.client.protocol_name}", True)
        self._write_connection_info(
            f"Adaptador: {self.client.adapter_name}\n"
            f"Protocolo: {self.client.protocol_name}\n"
            f"ATDPN: {self.client.protocol_number}\n"
            "Comunicación OBD-II establecida correctamente.\n"
        )
        self.live_running = True
        self.live_toggle_button.configure(text="Detener actualización")
        self.live_status_label.configure(text="Actualización activa", fg=COLORS["success"])
        self.start_scan()

    def disconnect(self) -> None:
        self.live_running = False
        if self.client:
            try:
                self.client.close()
            except Exception:
                self.logger.exception("Error al desconectar")
        self.client = None
        self.connected_at = None
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.live_toggle_button.configure(text="Iniciar actualización")
        self.live_status_label.configure(text="Detenido", fg=COLORS["muted"])
        self._set_status("Desconectado", False)
        self._write_connection_info("Conexión finalizada.\n")

    def _require_client(self) -> ELM327Client | None:
        if not self.client or not self.client.connected:
            messagebox.showwarning(APP_NAME, "Primero conecte el adaptador OBD-II o el simulador.")
            return None
        return self.client

    def start_scan(self) -> None:
        client = self._require_client()
        if not client:
            self.show_page("Conexión")
            return
        self.scan_button.configure(state="disabled")
        self.scan_progress.start(10)
        self.scan_state.configure(text="Escaneando...", fg=COLORS["primary"])
        self._set_status("Ejecutando escaneo automático...")
        self._run_worker(client.full_scan, "scan_complete")

    def _on_scan_complete(self, payload: object) -> None:
        self.scan_progress.stop()
        self.scan_button.configure(state="normal")
        if not isinstance(payload, VehicleScan):
            self._on_error(RuntimeError("Resultado de escaneo no válido"))
            return
        self.scan_result = payload
        self.current_dtcs = list(payload.dtcs)
        self.scan_state.configure(text="Escaneo finalizado", fg=COLORS["success"])
        self._set_status("Escaneo finalizado", True)
        text = [
            "ESCANEO AUTOMÁTICO COMPLETADO",
            "=" * 58,
            f"Adaptador: {payload.adapter}",
            f"Protocolo: {payload.protocol_name}",
            f"ATDPN: {payload.protocol_number}",
            f"VIN: {payload.vin or 'No disponible'}",
            f"PIDs disponibles: {len(payload.supported_pids)}",
            f"Monitores PID 0101: {payload.monitor_raw}",
            "",
            f"Códigos encontrados: {len(payload.dtcs)}",
        ]
        for item in payload.dtcs:
            record = self.db.lookup(item.code)
            text.append(f"  {item.code} [{item.status}] — {record.description}")
        self._set_text_widget(self.scan_text, "\n".join(text) + "\n")
        self._update_summary_from_scan(payload)
        self._populate_dtc_tree(payload.dtcs)

    def _update_summary_from_scan(self, scan: VehicleScan) -> None:
        self.vehicle_subtitle.configure(text="Identificación OBD-II completada")
        self.summary_vin.configure(text=f"VIN: {scan.vin or 'No disponible'}")
        self.summary_protocol.configure(text=f"Protocolo: {scan.protocol_name or 'No disponible'}")
        self.summary_dtc_count.configure(text=f"Códigos DTC: {len(scan.dtcs)}")
        self.summary_pid_count.configure(text=f"PIDs disponibles: {len(scan.supported_pids)}")
        confirmed = len([item for item in scan.dtcs if item.status.startswith("Confirmado")])
        score = max(0, 100 - confirmed * 18 - max(0, len(scan.dtcs) - confirmed) * 7)
        color = COLORS["success"] if score >= 80 else COLORS["warning"] if score >= 55 else COLORS["danger"]
        self.health_indicator.itemconfigure(self.health_arc, extent=-3.6 * score, outline=color)
        self.health_indicator.itemconfigure(self.health_text, text=f"{score}%")
        self.health_indicator.itemconfigure(self.health_label, text="Estado estimado", fill=color)

    def refresh_dtcs(self) -> None:
        client = self._require_client()
        if not client:
            return
        self._set_status("Leyendo códigos DTC...")
        self._run_worker(client.read_dtcs, "dtcs")

    def _on_dtcs(self, payload: object) -> None:
        dtcs = list(payload) if isinstance(payload, list) else []
        self.current_dtcs = dtcs
        if self.scan_result:
            self.scan_result.dtcs = dtcs
        self._populate_dtc_tree(dtcs)
        self._set_status(f"Lectura DTC finalizada: {len(dtcs)} códigos", True)

    def _populate_dtc_tree(self, dtcs: list[DTCResult]) -> None:
        for item in self.dtc_tree.get_children():
            self.dtc_tree.delete(item)
        for dtc in dtcs:
            record = self.db.lookup(dtc.code)
            self.dtc_tree.insert("", "end", values=(dtc.code, dtc.status, record.system, record.description))
        self.dtc_summary_label.configure(text=f"{len(dtcs)} códigos encontrados")
        self.summary_dtc_count.configure(text=f"Códigos DTC: {len(dtcs)}")

    def clear_dtcs(self) -> None:
        client = self._require_client()
        if not client:
            return
        if not messagebox.askyesno(APP_NAME, "¿Confirma el borrado de códigos DTC? La causa de la falla debe repararse antes de borrar."):
            return
        self._set_status("Borrando códigos DTC...")
        self._run_worker(client.clear_dtcs, "dtcs_cleared")

    def _on_dtcs_cleared(self, success: bool) -> None:
        if success:
            self.current_dtcs = []
            if self.scan_result:
                self.scan_result.dtcs = []
            self._populate_dtc_tree([])
            self._set_status("Códigos DTC borrados", True)
            messagebox.showinfo(APP_NAME, "La ECU confirmó el comando de borrado.")
        else:
            self._on_error(RuntimeError("La ECU no confirmó el borrado"))

    def toggle_live(self) -> None:
        if not self._require_client():
            return
        self.live_running = not self.live_running
        self.live_toggle_button.configure(text="Detener actualización" if self.live_running else "Iniciar actualización")
        self.live_status_label.configure(
            text="Actualización activa" if self.live_running else "Detenido",
            fg=COLORS["success"] if self.live_running else COLORS["muted"],
        )

    def _live_tick(self) -> None:
        if self._closing:
            return
        if self.live_running and not self.live_busy and self.client and self.client.connected:
            self.live_busy = True
            self._run_worker(self.client.read_live_data, "live", error_event="live_error")
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "live_error":
                    self.live_busy = False
                    self.logger.warning("Error temporal de datos en vivo: %s", payload)
                    self._append_console(f"ADVERTENCIA DATOS EN VIVO: {payload}")
                else:
                    self.events.put((event, payload))
                    break
        except queue.Empty:
            pass
        self.after(1000, self._live_tick)

    def _on_live_data(self, payload: object) -> None:
        self.live_busy = False
        if not isinstance(payload, dict):
            return
        self.current_live = payload
        elapsed = time.monotonic() - (self.connected_at or time.monotonic())
        for name, (value, _unit) in payload.items():
            if value is not None:
                self.history[name].append((elapsed, float(value)))
        self._populate_live_tree(payload)
        self._update_summary_metrics(payload)
        if self.pages["Gráficos"].winfo_ismapped():
            self.update_graph()

    def _populate_live_tree(self, data: dict[str, tuple[float | None, str]]) -> None:
        existing = {self.live_tree.set(item, "name"): item for item in self.live_tree.get_children()}
        for name, (value, unit) in data.items():
            formatted = "—" if value is None else f"{value:.2f}"
            state = "Disponible" if value is not None else "Sin respuesta"
            values = (name, formatted, unit, state)
            if name in existing:
                self.live_tree.item(existing[name], values=values)
            else:
                self.live_tree.insert("", "end", values=values)

    def _update_summary_metrics(self, data: dict[str, tuple[float | None, str]]) -> None:
        # Los controles existen desde la construcción de la página. La comprobación evita
        # cualquier llamada sobre referencias None y corrige el fallo histórico setText.
        for name in ("RPM motor", "Voltaje adaptador", "Caudal de combustible", "Nivel de combustible"):
            widget = self.metric_widgets.get(name)
            if widget is None or not widget.winfo_exists():
                continue
            value = data.get(name, (None, ""))[0]
            widget.configure(text="—" if value is None else f"{value:.2f}")

    def update_graph(self) -> None:
        name = self.graph_parameter.get() or "RPM motor"
        points = list(self.history.get(name, []))
        self.axes.clear()
        self.axes.grid(True, alpha=0.25)
        self.axes.set_title(name)
        self.axes.set_xlabel("Tiempo de sesión (s)")
        unit = ""
        for _cmd, definition in PID_DEFINITIONS.items():
            if definition[0] == name:
                unit = definition[1]
                break
        if name == "Voltaje adaptador":
            unit = "V"
        self.axes.set_ylabel(unit)
        if points:
            xs, ys = zip(*points)
            self.axes.plot(xs, ys, linewidth=1.8)
            self.axes.fill_between(xs, ys, alpha=0.08)
        else:
            self.axes.text(0.5, 0.5, "Sin datos registrados", transform=self.axes.transAxes, ha="center", va="center", color=COLORS["muted"])
        self.figure.tight_layout()
        self.graph_canvas.draw_idle()

    def clear_graph_history(self) -> None:
        self.history.clear()
        self.update_graph()

    def read_freeze_frame(self) -> None:
        client = self._require_client()
        if not client:
            return
        self._set_status("Leyendo Freeze Frame...")
        self._run_worker(client.read_freeze_frame, "freeze")

    def _on_freeze(self, payload: object) -> None:
        for item in self.freeze_tree.get_children():
            self.freeze_tree.delete(item)
        data = payload if isinstance(payload, dict) else {}
        for name, pair in data.items():
            value, unit = pair
            formatted = f"{value:.2f}" if isinstance(value, float) else str(value)
            self.freeze_tree.insert("", "end", values=(name, formatted, unit))
        self._set_status("Freeze Frame actualizado", True)

    def read_monitors(self) -> None:
        client = self._require_client()
        if not client:
            return
        self._set_status("Leyendo monitores OBD-II...")
        self._run_worker(client.read_monitor_status, "monitors")

    def _on_monitors(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        for key, label in self.monitor_labels.items():
            value = data.get(key, "—")
            if isinstance(value, bool):
                text = "Sí" if value else "No"
            else:
                text = str(value)
            label.configure(text=text, fg=COLORS["success"] if value is True else COLORS["text"])
        self._set_status("Monitores actualizados", True)

    def search_database(self) -> None:
        query = self.db_search_entry.get() if hasattr(self, "db_search_entry") else ""
        rows = self.db.search(query, limit=500)
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        for record in rows:
            self.db_tree.insert("", "end", values=(record.code, record.system, record.scope, record.description))
        self.db_count_label.configure(text=f"{len(rows)} resultados · {self.db.count():,} total".replace(",", "."))

    def generate_report(self) -> None:
        self._set_status("Generando informe PDF...")
        self.report_status.configure(text="Generando informe...")

        def operation() -> Path:
            return generate_pdf_report(self.scan_result, self.current_dtcs, self.current_live, self.db)

        self._run_worker(operation, "report")

    def _on_report(self, payload: object) -> None:
        if not isinstance(payload, Path):
            self._on_error(RuntimeError("No se obtuvo la ruta del informe"))
            return
        self.report_status.configure(text=f"Informe generado correctamente:\n{payload}", fg=COLORS["success"])
        self._set_status("Informe PDF generado", True if self.client and self.client.connected else None)
        if messagebox.askyesno(APP_NAME, "Informe generado correctamente. ¿Desea abrirlo ahora?"):
            try:
                os.startfile(str(payload))  # type: ignore[attr-defined]
            except Exception as exc:
                self.logger.warning("No fue posible abrir el informe: %s", exc)

    def open_report_folder(self) -> None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(REPORT_DIR))  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No fue posible abrir la carpeta:\n{exc}")

    def clear_console(self) -> None:
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def open_log(self) -> None:
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            LOG_FILE.touch(exist_ok=True)
            os.startfile(str(LOG_FILE))  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No fue posible abrir el registro:\n{exc}")

    def _on_error(self, payload: object) -> None:
        self.live_busy = False
        self.scan_progress.stop()
        self.scan_button.configure(state="normal")
        self.connect_button.configure(state="normal" if not (self.client and self.client.connected) else "disabled")
        message = str(payload)
        self._set_status(f"Error: {message}", False if not (self.client and self.client.connected) else True)
        self._append_console(f"ERROR: {message}")
        messagebox.showerror(APP_NAME, message)

    def on_close(self) -> None:
        self._closing = True
        self.live_running = False
        if self.client:
            try:
                self.client.close()
            except Exception:
                self.logger.exception("Error al cerrar la conexión")
        self.logger.info("Cierre %s", APP_NAME)
        self.destroy()
