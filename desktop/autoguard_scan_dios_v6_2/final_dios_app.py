from __future__ import annotations

import csv
import json
import queue
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageFont

import option_b_app as option_b_module
import premium_app as premium_module
from core import PID_DEFINITIONS, estimate_fuel_rate_from_maf
from deep_scan import DeepScanResult
from deep_scan_full import DeepScannerFull
from dtc_database import DTCRecord
from final_widgets import MultiTraceCanvas, SensorDetailWindow, TRACE_COLORS, enable_windows_dpi_awareness, format_value
from option_b_app import OptionBDeepScanApp
from premium_app import (
    APP_AUTHOR,
    BG,
    GREEN,
    Gauge,
    MUTED,
    ORANGE,
    ORANGE_DARK,
    ORANGE_LIGHT,
    PANEL,
    PANEL_2,
    RED,
    SIDEBAR,
    TEXT,
    YELLOW,
)

FINAL_VERSION = "6.2.0 FINAL DIOS HD"
FINAL_BUILD = "Escaneo profundo · Base offline ampliada · Interfaz Full HD"

premium_module.APP_VERSION = FINAL_VERSION
premium_module.APP_BUILD = FINAL_BUILD
option_b_module.DeepScanner = DeepScannerFull

SENSOR_SYSTEMS: dict[str, list[int]] = {
    "Motor": [0x0C, 0x04, 0x05, 0x0E, 0x11, 0x45, 0x47, 0x4C, 0x61, 0x62, 0x63],
    "Combustible": [0x06, 0x07, 0x08, 0x09, 0x0A, 0x22, 0x23, 0x2F, 0x52, 0x5E],
    "Admisión": [0x0B, 0x0F, 0x10, 0x33, 0x46],
    "Emisiones": [0x2C, 0x2D, 0x2E, 0x3C, 0x3D, 0x3E, 0x3F],
    "Temperaturas": [0x05, 0x0F, 0x3C, 0x3D, 0x3E, 0x3F, 0x46, 0x5C],
    "Eléctrico y operación": [0x42, 0x1F, 0x21, 0x30, 0x31, 0x4D, 0x4E, 0x5B],
}

DEFAULT_LIVE_PIDS = [0x0C, 0x0D, 0x05, 0x0B, 0x11, 0x10, 0x5E]


class FinalDiosApp(OptionBDeepScanApp):
    """Final AUTOGUARD desktop edition based on the approved Option A layout."""

    def __init__(self) -> None:
        self.sensor_windows: dict[int, SensorDetailWindow] = {}
        self.capture_snapshots: list[dict] = []
        self.session_started_at: float | None = None
        self.current_section_var: tk.StringVar | None = None
        self.multiscope_paused = False
        self.last_deep_scan_time = "--"
        super().__init__()
        self.title(f"AUTOGUARD SCAN DIOS v{FINAL_VERSION}")
        self.geometry("1600x900")
        self.minsize(1280, 720)
        try:
            dpi = self.winfo_fpixels("1i")
            self.tk.call("tk", "scaling", max(1.15, min(1.75, dpi / 72.0)))
        except Exception:
            pass
        self.after(60, self._maximize_window)
        self._show_page("Datos en vivo")

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except Exception:
            pass

    def _configure_style(self) -> None:
        super()._configure_style()
        style = ttk.Style(self)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background="#151D27", foreground=TEXT, padding=(14, 8), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#3B220C"), ("active", "#253242")], foreground=[("selected", ORANGE_LIGHT)])
        style.configure("Orange.Horizontal.TProgressbar", troughcolor="#0A1017", background=ORANGE, bordercolor="#0A1017", lightcolor=ORANGE, darkcolor=ORANGE_DARK)
        style.configure("Final.Treeview", background="#080D13", fieldbackground="#080D13", foreground="#E8EDF3", rowheight=27, font=("Segoe UI", 9), borderwidth=0)
        style.configure("Final.Treeview.Heading", background="#151E28", foreground="#F4F6F8", font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Final.Treeview", background=[("selected", "#56300A")], foreground=[("selected", "#FFFFFF")])

    def _build_sidebar(self) -> None:
        self.sidebar = tk.Frame(self.sidebar.master, bg="#080D13", width=124, highlightbackground="#283542", highlightthickness=1)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

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
        tk.Label(footer, text="Autor\nEsteban Cortez Richards", bg="#080D13", fg="#697786", font=("Segoe UI", 6), justify="center").pack(pady=(6, 0))

    def _build_header(self, parent) -> None:
        header = tk.Frame(parent, bg="#05090D", height=54, highlightbackground="#283440", highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)
        left = tk.Frame(header, bg="#05090D")
        left.pack(side="left", fill="y", padx=16)
        tk.Label(left, text="AUTOGUARD SCAN DIOS v6.2", bg="#05090D", fg=ORANGE, font=("Segoe UI", 17, "bold")).pack(side="left", pady=12)
        tk.Frame(left, bg="#273440", width=1, height=25).pack(side="left", padx=16, pady=14)
        self.current_section_var = tk.StringVar(value="Datos en vivo y osciloscopio")
        tk.Label(left, textvariable=self.current_section_var, bg="#05090D", fg="#C8D0D9", font=("Segoe UI", 10)).pack(side="left", pady=16)

        right = tk.Frame(header, bg="#05090D")
        right.pack(side="right", fill="y", padx=14)
        tk.Label(right, text="☼  Tema", bg="#05090D", fg="#C8D0D9", font=("Segoe UI", 9)).pack(side="left", padx=10, pady=16)
        self.header_protocol = tk.Label(right, text="Protocolo: sin conexión", bg="#05090D", fg=MUTED, font=("Segoe UI", 8))
        self.header_protocol.pack(side="left", padx=10, pady=16)
        self.header_status = tk.Label(right, text="● DESCONECTADO", bg="#05090D", fg=MUTED, font=("Segoe UI", 8, "bold"))
        self.header_status.pack(side="left", padx=10, pady=16)

    def _build_pages(self) -> None:
        super()._build_pages()
        self._build_modules_page(self._new_page("Módulos ECU"))
        self._build_vehicle_page(self._new_page("Información del vehículo"))
        self._build_history_page(self._new_page("Historial"))
        self._build_help_page(self._new_page("Ayuda"))

    def _install_deep_scan_page(self) -> None:
        page = self._new_page("Escaneo profundo")
        self._build_deep_scan(page)

    def _show_page(self, name: str) -> None:
        if not hasattr(self, "pages") or name not in self.pages:
            return
        self.pages[name].tkraise()
        for page, button in self.nav_buttons.items():
            active = page == name
            button.configure(
                bg="#3A210C" if active else "#080D13",
                fg=ORANGE_LIGHT if active else "#AEB8C4",
                highlightbackground=ORANGE if active else "#080D13",
            )
        labels = {
            "Datos en vivo": "Datos en vivo y osciloscopio",
            "Escaneo profundo": "Escaneo profundo de ECU y módulos",
            "DTC y soluciones": "Códigos DTC, descripción y solución offline",
            "Pruebas funcionales": "Tablas y pruebas guiadas",
            "Módulos ECU": "Módulos detectados y cobertura de red",
            "Información": "Planificación y base técnica local",
            "Información del vehículo": "Identificación del vehículo y ECU",
            "Informe Premium": "Informe profesional Premium con gráficos",
            "Historial": "Historial de sesiones y capturas",
            "Conexión": "Conexión y ajustes ELM327",
            "Ayuda": "Ayuda y alcance técnico",
        }
        if self.current_section_var is not None:
            self.current_section_var.set(labels.get(name, name))

    def _panel(self, parent, **kwargs) -> tk.Frame:
        return tk.Frame(parent, bg=PANEL, highlightbackground="#2C3A48", highlightthickness=1, **kwargs)

    def _build_live(self, page: tk.Frame) -> None:
        page.configure(bg=BG)
        connection = self._panel(page, height=91)
        connection.pack(fill="x", pady=(0, 8))
        connection.pack_propagate(False)
        for column in range(4):
            connection.columnconfigure(column, weight=1)
        self.live_connection_var = tk.StringVar(value="Desconectado")
        self.live_protocol_var = tk.StringVar(value="Sin detectar")
        self.live_vehicle_var = tk.StringVar(value="Vehículo no identificado")
        self.live_session_var = tk.StringVar(value="00:00:00")
        blocks = [
            ("Estado conexión ELM327", self.live_connection_var, "Puerto / adaptador"),
            ("Protocolo detectado", self.live_protocol_var, "ECU motor · identificación"),
            ("Vehículo", self.live_vehicle_var, "VIN / ECU desde escaneo profundo"),
            ("Tiempo de sesión", self.live_session_var, "Registro de datos activo"),
        ]
        for index, (title, variable, subtitle) in enumerate(blocks):
            block = tk.Frame(connection, bg=PANEL)
            block.grid(row=0, column=index, sticky="nsew", padx=14, pady=10)
            tk.Label(block, text=title, bg=PANEL, fg="#AAB5C1", font=("Segoe UI", 8)).pack(anchor="w")
            value = tk.Label(block, textvariable=variable, bg=PANEL, fg=GREEN if index == 0 else TEXT, font=("Segoe UI", 12, "bold"))
            value.pack(anchor="w", pady=(3, 1))
            tk.Label(block, text=subtitle, bg=PANEL, fg=MUTED, font=("Segoe UI", 7)).pack(anchor="w")
            if index < 3:
                tk.Frame(connection, bg="#33414F", width=1).grid(row=0, column=index, sticky="e", pady=13)
        ttk.Button(connection, text="Finalizar sesión", style="Accent.TButton", command=self._finish_session).place(relx=0.895, rely=0.52, anchor="center")

        upper = tk.Frame(page, bg=BG)
        upper.pack(fill="both", expand=True)
        upper.columnconfigure(0, weight=0, minsize=310)
        upper.columnconfigure(1, weight=5)
        upper.columnconfigure(2, weight=3)
        upper.rowconfigure(0, weight=1)

        sensor_panel = self._panel(upper, width=310)
        sensor_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        sensor_panel.grid_propagate(False)
        tk.Label(sensor_panel, text="SENSORES POR SISTEMA", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        self.sensor_search_var = tk.StringVar()
        search = ttk.Entry(sensor_panel, textvariable=self.sensor_search_var)
        search.pack(fill="x", padx=10, pady=(0, 7))
        search.bind("<KeyRelease>", lambda _event: self._filter_sensor_tree())
        self.sensor_tree = ttk.Treeview(sensor_panel, columns=("check", "pid", "unit"), show="tree headings", style="Final.Treeview")
        self.sensor_tree.heading("#0", text="Sensor / sistema")
        self.sensor_tree.heading("check", text="")
        self.sensor_tree.heading("pid", text="PID")
        self.sensor_tree.heading("unit", text="Unidad")
        self.sensor_tree.column("#0", width=174, anchor="w")
        self.sensor_tree.column("check", width=32, anchor="center")
        self.sensor_tree.column("pid", width=55, anchor="center")
        self.sensor_tree.column("unit", width=48, anchor="center")
        sensor_scroll = ttk.Scrollbar(sensor_panel, orient="vertical", command=self.sensor_tree.yview)
        self.sensor_tree.configure(yscrollcommand=sensor_scroll.set)
        self.sensor_tree.pack(side="left", fill="both", expand=True, padx=(9, 0), pady=(0, 50))
        sensor_scroll.pack(side="right", fill="y", padx=(0, 8), pady=(0, 50))
        self.sensor_tree.bind("<Button-1>", self._sensor_tree_click)
        self.sensor_tree.bind("<Double-1>", self._sensor_tree_double_click)
        self.pid_vars = {pid: tk.BooleanVar(value=pid in DEFAULT_LIVE_PIDS) for pid in PID_DEFINITIONS}
        self.sensor_tree_items: dict[int, str] = {}
        self._populate_sensor_tree()
        sensor_buttons = tk.Frame(sensor_panel, bg=PANEL)
        sensor_buttons.place(relx=0.03, rely=0.92, relwidth=0.94, height=38)
        ttk.Button(sensor_buttons, text="Seleccionar todos", command=lambda: self._set_sensor_selection(True)).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(sensor_buttons, text="Limpiar", command=lambda: self._set_sensor_selection(False)).pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.selected_sensor_label = tk.Label(sensor_panel, text="Seleccionados 7", bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.selected_sensor_label.place(relx=0.04, rely=0.875)

        scope_panel = self._panel(upper)
        scope_panel.grid(row=0, column=1, sticky="nsew", padx=6)
        scope_toolbar = tk.Frame(scope_panel, bg=PANEL)
        scope_toolbar.pack(fill="x", padx=10, pady=7)
        tk.Label(scope_toolbar, text="OSCILOSCOPIO DE DATOS EN VIVO", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(scope_toolbar, text="Tiempo base:", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(30, 4))
        self.time_window_var = tk.StringVar(value="10 s")
        time_combo = ttk.Combobox(scope_toolbar, textvariable=self.time_window_var, values=["5 s", "10 s", "20 s", "30 s", "60 s"], state="readonly", width=8)
        time_combo.pack(side="left")
        time_combo.bind("<<ComboboxSelected>>", lambda _event: self._change_time_window())
        self.pause_button = ttk.Button(scope_toolbar, text="Pausar", command=self._toggle_multiscope_pause)
        self.pause_button.pack(side="right")
        ttk.Button(scope_toolbar, text="Iniciar lectura", style="Accent.TButton", command=self._start_live).pack(side="right", padx=6)
        ttk.Button(scope_toolbar, text="Detener", command=self._stop_live).pack(side="right")
        self.multi_scope = MultiTraceCanvas(scope_panel)
        self.multi_scope.bind_owner(self)
        self.multi_scope.pack(fill="both", expand=True, padx=9, pady=(0, 9))
        self.multi_scope.set_pids(DEFAULT_LIVE_PIDS)

        trace_panel = self._panel(upper)
        trace_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        tk.Label(trace_panel, text="LECTURAS Y TRAZAS", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=8)
        columns = ("parameter", "value", "unit", "minimum", "maximum", "pid")
        self.live_tree = ttk.Treeview(trace_panel, columns=columns, show="headings", style="Final.Treeview")
        headings = [
            ("parameter", "Sensor", 165), ("value", "Valor", 67), ("unit", "Unidad", 52),
            ("minimum", "Mín", 58), ("maximum", "Máx", 58), ("pid", "PID", 58),
        ]
        for column, title, width in headings:
            self.live_tree.heading(column, text=title)
            self.live_tree.column(column, width=width, anchor="w")
        trace_scroll = ttk.Scrollbar(trace_panel, orient="vertical", command=self.live_tree.yview)
        self.live_tree.configure(yscrollcommand=trace_scroll.set)
        self.live_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        trace_scroll.pack(side="right", fill="y", padx=(0, 8), pady=(0, 8))
        self.live_items = {}
        for pid in DEFAULT_LIVE_PIDS:
            name, unit = PID_DEFINITIONS[pid]
            self.live_items[pid] = self.live_tree.insert("", "end", values=(name, "--", unit, "--", "--", f"01{pid:02X}"))
        self.live_tree.bind("<Double-1>", self._trace_double_click)

        lower = tk.Frame(page, bg=BG)
        lower.pack(fill="x", pady=(8, 0))
        lower.columnconfigure(0, weight=3)
        lower.columnconfigure(1, weight=4)
        flow_panel = self._panel(lower, height=196)
        flow_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        flow_panel.grid_propagate(False)
        tk.Label(flow_panel, text="FLUJO DE COMBUSTIBLE [L/h]", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(9, 2))
        flow_body = tk.Frame(flow_panel, bg=PANEL)
        flow_body.pack(fill="both", expand=True, padx=9, pady=(0, 8))
        flow_body.columnconfigure(0, weight=1)
        flow_body.columnconfigure(1, weight=1)
        self.direct_flow_value = tk.StringVar(value="--")
        self.estimated_flow_value = tk.StringVar(value="--")
        self.flow_difference_var = tk.StringVar(value="--")
        for index, (title, variable) in enumerate((("PID 015E · lectura directa ECU", self.direct_flow_value), ("Estimado desde MAF", self.estimated_flow_value))):
            card = tk.Frame(flow_body, bg="#0A1118", highlightbackground="#293846", highlightthickness=1)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 4) if index == 0 else (4, 0))
            tk.Label(card, text=title, bg="#0A1118", fg=MUTED, font=("Segoe UI", 8)).pack(pady=(8, 2))
            tk.Label(card, textvariable=variable, bg="#0A1118", fg=ORANGE, font=("Segoe UI", 27, "bold")).pack()
            tk.Label(card, text="L/h", bg="#0A1118", fg=TEXT, font=("Segoe UI", 9)).pack()
        self.fuel_source_label = tk.Label(flow_panel, text="Estado: esperando datos", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold"))
        self.fuel_source_label.place(relx=0.035, rely=0.88)
        tk.Label(flow_panel, textvariable=self.flow_difference_var, bg=PANEL, fg=ORANGE_LIGHT, font=("Segoe UI", 9, "bold")).place(relx=0.72, rely=0.88)

        gauge_panel = self._panel(lower, height=196)
        gauge_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        gauge_panel.grid_propagate(False)
        for column in range(4):
            gauge_panel.columnconfigure(column, weight=1)
        self.live_gauge_voltage = Gauge(gauge_panel, "VOLTAJE", "V", 8, 18, 15.2, 16.4, size=174)
        self.live_gauge_map = Gauge(gauge_panel, "PRESIÓN MAP", "kPa", 0, 255, 110, 180, size=174)
        self.live_gauge_oil = Gauge(gauge_panel, "TEMP. ACEITE", "°C", 40, 200, 115, 145, size=174)
        self.live_gauge_coolant = Gauge(gauge_panel, "REFRIGERANTE", "°C", 40, 130, 100, 115, size=174)
        for index, gauge in enumerate((self.live_gauge_voltage, self.live_gauge_map, self.live_gauge_oil, self.live_gauge_coolant)):
            gauge.grid(row=0, column=index, sticky="nsew", padx=2, pady=2)

        bottom = tk.Frame(page, bg=BG, height=150)
        bottom.pack(fill="x", pady=(8, 0))
        bottom.pack_propagate(False)
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=3)
        bottom.columnconfigure(2, weight=4)
        dtc_panel = self._panel(bottom)
        dtc_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(dtc_panel, text="DTC ACTIVOS", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=7)
        self.live_dtc_tree = ttk.Treeview(dtc_panel, columns=("code", "description"), show="headings", height=3, style="Final.Treeview")
        self.live_dtc_tree.heading("code", text="Código")
        self.live_dtc_tree.heading("description", text="Descripción")
        self.live_dtc_tree.column("code", width=75)
        self.live_dtc_tree.column("description", width=300)
        self.live_dtc_tree.pack(fill="both", expand=True, padx=8)
        ttk.Button(dtc_panel, text="Ver todos y soluciones", command=lambda: self._show_page("DTC y soluciones")).pack(anchor="e", padx=8, pady=5)

        info_panel = self._panel(bottom)
        info_panel.grid(row=0, column=1, sticky="nsew", padx=6)
        tk.Label(info_panel, text="INFORMACIÓN ADICIONAL", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=7)
        self.live_mil_var = tk.StringVar(value="MIL: no informado")
        self.live_monitor_var = tk.StringVar(value="Monitores OBD-II: no leídos")
        self.live_mode_var = tk.StringVar(value="Modo de prueba: lectura estándar")
        for variable in (self.live_mil_var, self.live_monitor_var, self.live_mode_var):
            tk.Label(info_panel, textvariable=variable, bg=PANEL, fg="#C6CED7", font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=10, pady=4)

        export_panel = self._panel(bottom)
        export_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        tk.Label(export_panel, text="CAPTURA Y EXPORTACIÓN", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=7)
        exports = tk.Frame(export_panel, bg=PANEL)
        exports.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        for column in range(4):
            exports.columnconfigure(column, weight=1)
        actions = [
            ("Capturar datos", self._capture_sample),
            ("Guardar captura", self._save_capture),
            ("Exportar CSV", self._export_live_csv),
            ("Exportar gráfica", self._export_live_graph),
        ]
        for index, (label, command) in enumerate(actions):
            ttk.Button(exports, text=label, command=command).grid(row=0, column=index, sticky="nsew", padx=3, pady=3)

        self.selected_sensor_label.configure(text=f"Seleccionados {len(DEFAULT_LIVE_PIDS)}")

    def _populate_sensor_tree(self) -> None:
        for item in self.sensor_tree.get_children():
            self.sensor_tree.delete(item)
        self.sensor_tree_items.clear()
        included: set[int] = set()
        for system, pids in SENSOR_SYSTEMS.items():
            unique = [pid for pid in pids if pid in PID_DEFINITIONS and pid not in included]
            included.update(unique)
            parent = self.sensor_tree.insert("", "end", iid=f"system:{system}", text=f"▾ {system} ({len(unique)})", values=("", "", ""), open=system in {"Motor", "Combustible"})
            for pid in unique:
                name, unit = PID_DEFINITIONS[pid]
                item = self.sensor_tree.insert(parent, "end", iid=f"pid:{pid:02X}", text=name, values=("☑" if self.pid_vars[pid].get() else "☐", f"01{pid:02X}", unit))
                self.sensor_tree_items[pid] = item
        remaining = [pid for pid in PID_DEFINITIONS if pid not in included]
        parent = self.sensor_tree.insert("", "end", iid="system:Otros", text=f"▸ Otros PID ({len(remaining)})", values=("", "", ""), open=False)
        for pid in remaining:
            name, unit = PID_DEFINITIONS[pid]
            item = self.sensor_tree.insert(parent, "end", iid=f"pid:{pid:02X}", text=name, values=("☑" if self.pid_vars[pid].get() else "☐", f"01{pid:02X}", unit))
            self.sensor_tree_items[pid] = item

    def _filter_sensor_tree(self) -> None:
        query = self.sensor_search_var.get().strip().casefold()
        if not query:
            self._populate_sensor_tree()
            return
        for item in self.sensor_tree.get_children():
            self.sensor_tree.delete(item)
        self.sensor_tree_items.clear()
        parent = self.sensor_tree.insert("", "end", iid="system:Resultados", text="Resultados", open=True)
        for pid, (name, unit) in PID_DEFINITIONS.items():
            searchable = f"{name} 01{pid:02X} {unit}".casefold()
            if query in searchable:
                item = self.sensor_tree.insert(parent, "end", iid=f"pid:{pid:02X}", text=name, values=("☑" if self.pid_vars[pid].get() else "☐", f"01{pid:02X}", unit))
                self.sensor_tree_items[pid] = item

    def _sensor_tree_click(self, event) -> None:
        item = self.sensor_tree.identify_row(event.y)
        if not item:
            return
        if item.startswith("pid:"):
            pid = int(item.split(":", 1)[1], 16)
            self.pid_vars[pid].set(not self.pid_vars[pid].get())
            self._refresh_sensor_selection()
        elif item.startswith("system:"):
            children = self.sensor_tree.get_children(item)
            if children:
                selected = all(self.pid_vars[int(child.split(":", 1)[1], 16)].get() for child in children if child.startswith("pid:"))
                for child in children:
                    if child.startswith("pid:"):
                        self.pid_vars[int(child.split(":", 1)[1], 16)].set(not selected)
                self._refresh_sensor_selection()

    def _sensor_tree_double_click(self, event) -> None:
        item = self.sensor_tree.identify_row(event.y)
        if item.startswith("pid:"):
            self._open_sensor_window(int(item.split(":", 1)[1], 16))

    def _trace_double_click(self, event) -> None:
        item = self.live_tree.identify_row(event.y)
        if not item:
            return
        values = self.live_tree.item(item, "values")
        if values and str(values[-1]).startswith("01"):
            self._open_sensor_window(int(str(values[-1])[2:], 16))

    def _set_sensor_selection(self, selected: bool) -> None:
        for variable in self.pid_vars.values():
            variable.set(selected)
        self._refresh_sensor_selection()

    def _refresh_sensor_selection(self) -> None:
        for pid, item in self.sensor_tree_items.items():
            if self.sensor_tree.exists(item):
                values = list(self.sensor_tree.item(item, "values"))
                if values:
                    values[0] = "☑" if self.pid_vars[pid].get() else "☐"
                    self.sensor_tree.item(item, values=values)
        selected = [pid for pid, variable in self.pid_vars.items() if variable.get()]
        self.selected_sensor_label.configure(text=f"Seleccionados {len(selected)}")
        self.multi_scope.set_pids(selected[:8])
        visible = set(selected)
        existing = set(self.live_items)
        for pid in existing - visible:
            self.live_tree.delete(self.live_items.pop(pid))
        for pid in selected:
            if pid not in self.live_items:
                name, unit = PID_DEFINITIONS[pid]
                self.live_items[pid] = self.live_tree.insert("", "end", values=(name, "--", unit, "--", "--", f"01{pid:02X}"))

    def _open_sensor_window(self, pid: int) -> None:
        window = self.sensor_windows.get(pid)
        if window is not None and window.winfo_exists():
            window.lift()
            window.focus_force()
            return
        self.pid_vars[pid].set(True)
        self._refresh_sensor_selection()
        window = SensorDetailWindow(self, pid)
        self.sensor_windows[pid] = window

    def _toggle_multiscope_pause(self) -> None:
        self.multiscope_paused = not self.multiscope_paused
        self.multi_scope.set_paused(self.multiscope_paused)
        self.pause_button.configure(text="Reanudar" if self.multiscope_paused else "Pausar")

    def _change_time_window(self) -> None:
        value = self.time_window_var.get().split()[0]
        try:
            self.multi_scope.set_time_window(float(value))
        except ValueError:
            pass

    def _finish_session(self) -> None:
        self._stop_live(update_status=False)
        self._record_history("Sesión finalizada", f"Muestras: {sum(len(items) for items in self.history.values())}")
        self._disconnect()
        self.session_started_at = None
        self.live_session_var.set("00:00:00")

    def _capture_sample(self) -> None:
        snapshot = {
            "timestamp": time.time(),
            "protocol": self.client.protocol,
            "fuel_source": self.fuel_source,
            "values": {f"01{pid:02X}": value for pid, value in self.latest_values.items()},
        }
        self.capture_snapshots.append(snapshot)
        self._record_history("Captura de datos", f"{len(snapshot['values'])} parámetros")
        self._set_status(f"Captura registrada · {len(snapshot['values'])} parámetros")

    def _save_capture(self) -> None:
        if not self.capture_snapshots:
            self._capture_sample()
        target = filedialog.asksaveasfilename(title="Guardar captura AUTOGUARD", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"AUTOGUARD_CAPTURA_{time.strftime('%Y%m%d_%H%M%S')}.json")
        if not target:
            return
        Path(target).write_text(json.dumps(self.capture_snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
        self._set_status(f"Captura guardada: {target}")

    def _export_live_csv(self) -> None:
        selected = [pid for pid, variable in self.pid_vars.items() if variable.get() and self.history.get(pid)]
        if not selected:
            messagebox.showinfo("Exportar CSV", "No existen datos registrados en los sensores seleccionados.")
            return
        target = filedialog.asksaveasfilename(title="Exportar sesión CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile=f"AUTOGUARD_SESION_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        if not target:
            return
        rows: list[tuple[float, int, float]] = []
        for pid in selected:
            rows.extend((timestamp, pid, float(value)) for timestamp, value in self.history[pid])
        rows.sort(key=lambda row: row[0])
        with Path(target).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["fecha_hora", "pid", "sensor", "valor", "unidad"])
            for timestamp, pid, value in rows:
                name, unit = PID_DEFINITIONS[pid]
                writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)), f"01{pid:02X}", name, f"{value:.5f}", unit])
        self._record_history("Exportación CSV", str(target))

    def _export_live_graph(self) -> None:
        selected = [pid for pid, variable in self.pid_vars.items() if variable.get() and self.history.get(pid)][:8]
        if not selected:
            messagebox.showinfo("Exportar gráfica", "No existen muestras para graficar.")
            return
        target = filedialog.asksaveasfilename(title="Exportar gráfica HD", defaultextension=".png", filetypes=[("PNG", "*.png")], initialfile=f"AUTOGUARD_GRAFICA_HD_{time.strftime('%Y%m%d_%H%M%S')}.png")
        if not target:
            return
        width, height = 1920, 1080
        image = Image.new("RGB", (width, height), "#05090E")
        draw = ImageDraw.Draw(image)
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 38)
            body_font = ImageFont.truetype("arial.ttf", 22)
        except OSError:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        draw.text((70, 45), "AUTOGUARD SCAN DIOS v6.2 · GRÁFICA DE SESIÓN", fill="#FF7900", font=title_font)
        left, top, right, bottom = 100, 150, 1840, 950
        for index in range(11):
            x = left + (right - left) * index / 10
            draw.line((x, top, x, bottom), fill="#263544", width=1)
        for index in range(9):
            y = top + (bottom - top) * index / 8
            draw.line((left, y, right, y), fill="#263544", width=1)
        lanes = len(selected)
        for lane, pid in enumerate(selected):
            samples = list(self.history[pid])
            values = [float(value) for _, value in samples]
            minimum, maximum = min(values), max(values)
            span = max(maximum - minimum, 0.001)
            lane_h = (bottom - top) / lanes
            center = top + lane_h * (lane + 0.5)
            color = TRACE_COLORS[lane % len(TRACE_COLORS)]
            first, last = samples[0][0], samples[-1][0]
            duration = max(last - first, 0.001)
            points = []
            for timestamp, value in samples[-800:]:
                x = left + (timestamp - first) / duration * (right - left)
                y = center + lane_h * 0.32 - (float(value) - minimum) / span * lane_h * 0.64
                points.append((x, y))
            if len(points) > 1:
                draw.line(points, fill=color, width=4)
            name, unit = PID_DEFINITIONS[pid]
            draw.text((left + 10, top + lane * lane_h + 5), f"{name} · {format_value(values[-1])} {unit}", fill=color, font=body_font)
        image.save(target, quality=96)
        self._record_history("Gráfica HD exportada", str(target))

    def _build_modules_page(self, page: tk.Frame) -> None:
        self._section_title(page, "Módulos ECU detectados", "Cobertura de red, direcciones CAN, identificación UDS y códigos por módulo")
        self.modules_tree_final = ttk.Treeview(page, columns=("request", "response", "family", "vin", "serial", "software", "dtcs"), show="headings", style="Final.Treeview")
        for column, title, width in (("request", "Solicitud", 95), ("response", "Respuesta", 95), ("family", "Módulo / familia", 250), ("vin", "VIN", 185), ("serial", "N.º serie", 160), ("software", "Software", 180), ("dtcs", "DTC UDS", 260)):
            self.modules_tree_final.heading(column, text=title)
            self.modules_tree_final.column(column, width=width, anchor="w")
        scroll = ttk.Scrollbar(page, orient="vertical", command=self.modules_tree_final.yview)
        self.modules_tree_final.configure(yscrollcommand=scroll.set)
        self.modules_tree_final.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_vehicle_page(self, page: tk.Frame) -> None:
        self._section_title(page, "Información del vehículo y ECU", "Datos Mode 09, UDS y protocolo detectado")
        self.vehicle_tree_final = ttk.Treeview(page, columns=("item", "value"), show="headings", style="Final.Treeview")
        self.vehicle_tree_final.heading("item", text="Elemento")
        self.vehicle_tree_final.heading("value", text="Información detectada")
        self.vehicle_tree_final.column("item", width=300)
        self.vehicle_tree_final.column("value", width=800)
        self.vehicle_tree_final.pack(fill="both", expand=True)

    def _build_history_page(self, page: tk.Frame) -> None:
        self._section_title(page, "Historial y registros de sesión", "Capturas, escaneos y exportaciones realizadas durante la ejecución")
        self.history_tree_final = ttk.Treeview(page, columns=("time", "event", "detail"), show="headings", style="Final.Treeview")
        for column, title, width in (("time", "Fecha / hora", 190), ("event", "Evento", 250), ("detail", "Detalle", 750)):
            self.history_tree_final.heading(column, text=title)
            self.history_tree_final.column(column, width=width, anchor="w")
        self.history_tree_final.pack(fill="both", expand=True)
        self._record_history("Aplicación iniciada", FINAL_VERSION)

    def _build_help_page(self, page: tk.Frame) -> None:
        self._section_title(page, "Ayuda y alcance técnico", "Uso responsable del diagnóstico AUTOGUARD")
        panel = self._panel(page)
        panel.pack(fill="both", expand=True)
        text = tk.Text(panel, bg="#070C12", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 10))
        text.pack(fill="both", expand=True, padx=14, pady=14)
        text.insert("end", "AUTOGUARD SCAN DIOS v6.2 FINAL DIOS HD\n\n")
        text.insert("end", "• El escaneo profundo consulta toda la información estándar y UDS de solo lectura que el vehículo y el adaptador publiquen.\n\n")
        text.insert("end", "• Los datos propietarios protegidos pueden requerir interfaz J2534, DoIP, CAN-FD, credenciales de seguridad y documentación OEM.\n\n")
        text.insert("end", "• Un DTC no confirma por sí solo una pieza defectuosa. Utilice causas, pasos y soluciones offline como guía y valide con mediciones.\n\n")
        text.insert("end", "• Las ventanas individuales permiten observar cada sensor, sus estadísticas y tendencia temporal.\n\n")
        text.insert("end", "• El osciloscopio de la aplicación muestra telemetría ECU. Las formas de onda eléctricas CKP, CMP, bobinas, inyectores y CAN requieren osciloscopio físico.\n\n")
        text.insert("end", f"Autor: {APP_AUTHOR}\nVersión: {FINAL_VERSION}")
        text.configure(state="disabled")

    def _record_history(self, event: str, detail: str) -> None:
        if hasattr(self, "history_tree_final"):
            self.history_tree_final.insert("", 0, values=(time.strftime("%d-%m-%Y %H:%M:%S"), event, detail))

    def _populate_dtc_tree(self, records: list[tuple[DTCRecord, str]]) -> None:
        super()._populate_dtc_tree(records)
        if hasattr(self, "live_dtc_tree"):
            for item in self.live_dtc_tree.get_children():
                self.live_dtc_tree.delete(item)
            seen: set[str] = set()
            for record, _status in records:
                if record.code in seen:
                    continue
                seen.add(record.code)
                self.live_dtc_tree.insert("", "end", values=(record.code, record.description))
                if len(seen) >= 4:
                    break

    def _populate_deep_result(self, result: DeepScanResult) -> None:
        super()._populate_deep_result(result)
        self.last_deep_scan_time = time.strftime("%d-%m-%Y %H:%M:%S")
        self._record_history("Escaneo profundo finalizado", f"{len(result.modules)} módulos · {len(result.supported_pids)} PID")
        for tree in (self.modules_tree_final, self.vehicle_tree_final):
            for item in tree.get_children():
                tree.delete(item)
        for module in result.modules:
            self.modules_tree_final.insert("", "end", values=(module.request_header, module.response_header or "--", module.family, module.vin or "--", module.serial_number or "--", module.software_number or "--", ", ".join(module.uds_dtcs) if module.uds_dtcs else "--"))
        self.vehicle_tree_final.insert("", "end", values=("Protocolo", result.protocol))
        for key, value in result.adapter.items():
            self.vehicle_tree_final.insert("", "end", values=(f"Adaptador · {key}", value))
        for key, value in result.vehicle_information.items():
            self.vehicle_tree_final.insert("", "end", values=(key, value))
        vin = str(result.vehicle_information.get("VIN", "")).strip()
        name = str(result.vehicle_information.get("Nombre ECU", "")).strip()
        if vin or name:
            self.live_vehicle_var.set(" · ".join(value for value in (vin[:17], name[:28]) if value))
        standard_records: list[tuple[DTCRecord, str]] = []
        for status, codes in result.dtcs.items():
            for code in codes:
                records = self.database.lookup(code)
                if records:
                    standard_records.extend((record, status) for record in records)
        if standard_records:
            self._populate_dtc_tree(standard_records)
        self.live_mil_var.set(f"MIL: {'Encendida' if result.readiness.get('mil_encendida') else 'Apagada'}")
        available = result.readiness.get("monitores_disponibles") or result.readiness.get("available")
        self.live_monitor_var.set(f"Monitores OBD-II: {available if available is not None else 'consultados'}")
        self.live_mode_var.set(f"Mode 06: {len(result.mode06_tests)} respuestas · ECU: {len(result.modules)}")

    def _drain_queues(self) -> None:
        super()._drain_queues()
        if self.client.connected:
            if self.session_started_at is None:
                self.session_started_at = time.time()
                self._record_history("Conexión iniciada", self.client.protocol)
            elapsed = max(0, int(time.time() - self.session_started_at))
            self.live_session_var.set(time.strftime("%H:%M:%S", time.gmtime(elapsed)))
            self.live_connection_var.set("● Conectado")
            self.live_protocol_var.set(self.client.protocol[:36])
        else:
            self.live_connection_var.set("Desconectado")
            self.live_protocol_var.set("Sin detectar")
        selected = [pid for pid, variable in self.pid_vars.items() if variable.get()]
        self.multi_scope.set_pids(selected[:8])
        self.multi_scope.redraw()
        direct = self.latest_values.get(0x5E)
        maf = self.latest_values.get(0x10)
        estimated = estimate_fuel_rate_from_maf(maf) if maf is not None else None
        if direct is not None and "directa" in self.fuel_source.casefold():
            self.direct_flow_value.set(format_value(direct))
        else:
            self.direct_flow_value.set("N/D")
        self.estimated_flow_value.set(format_value(estimated) if estimated is not None else "N/D")
        if direct is not None and estimated not in (None, 0):
            difference = abs(direct - estimated) / estimated * 100
            self.flow_difference_var.set(f"Diferencia {difference:.1f} %")
        else:
            self.flow_difference_var.set(self.fuel_source)
        self.live_gauge_voltage.set_value(self.latest_values.get(0x42, 8), 0x42 in self.latest_values)
        self.live_gauge_map.set_value(self.latest_values.get(0x0B, 0), 0x0B in self.latest_values)
        self.live_gauge_oil.set_value(self.latest_values.get(0x5C, 40), 0x5C in self.latest_values)
        self.live_gauge_coolant.set_value(self.latest_values.get(0x05, 40), 0x05 in self.latest_values)


def main() -> None:
    enable_windows_dpi_awareness()
    try:
        app = FinalDiosApp()
        app.mainloop()
    except Exception as exc:
        log_dir = Path.home() / "AppData" / "Local" / "Autoguard" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "AUTOGUARD_FINAL_DIOS_INICIO_ERROR.log"
        log_file.write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{type(exc).__name__}: {exc}\n", encoding="utf-8")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("AUTOGUARD SCAN DIOS", f"No fue posible iniciar la versión final.\n\n{exc}\n\nRegistro: {log_file}")
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
