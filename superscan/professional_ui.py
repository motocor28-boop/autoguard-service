from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Mapping, Sequence

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .config import APP_NAME, APP_VERSION, COLORS, LIVE_PID_ORDER, LOG_FILE, PID_DEFINITIONS, REPORT_DIR
from .dtc_database import TOTAL_DTC_RECORDS
from .obd import DTCResult, VehicleScan, available_serial_ports
from .professional_reporting import generate_professional_report
from .solution_engine import DiagnosticGuide, OfflineSolutionDatabase
from .ui import SuperScanApp


PRO = {
    "bg": "#05090D",
    "sidebar": "#080D12",
    "panel": "#0E151C",
    "panel2": "#121B24",
    "panel3": "#17222D",
    "border": "#273542",
    "blue": "#168DFF",
    "blue2": "#0B63BE",
    "gold": "#E2A72E",
    "green": "#21C36B",
    "orange": "#F39C12",
    "red": "#E64545",
    "purple": "#8E5BE8",
    "cyan": "#28B7C7",
    "text": "#F5F7FA",
    "muted": "#94A2AF",
    "muted2": "#657482",
    "white": "#FFFFFF",
}

SEVERITY = {
    "CRÍTICA": PRO["red"],
    "ALTA": "#F06837",
    "MEDIA": PRO["orange"],
    "BAJA": PRO["green"],
}

NAV_ITEMS = [
    ("Inicio", "Resumen"),
    ("Conexión", "Conexión"),
    ("Diagnóstico", "Escaneo"),
    ("Códigos DTC", "Códigos DTC"),
    ("Datos en Vivo", "Datos en vivo"),
    ("Gráficos HD", "Gráficos"),
    ("Freeze Frame", "Freeze Frame"),
    ("Monitores OBD-II", "Monitores"),
    ("Solución Guiada", "Solución Guiada"),
    ("Base Offline", "Base DTC"),
    ("Informes", "Informe"),
    ("Historial", "Historial"),
    ("Configuración", "Configuración"),
    ("Consola Técnica", "Consola"),
]


class ProfessionalSuperScanApp(SuperScanApp):
    """Interfaz profesional oscura sobre el motor OBD-II probado de SuperScan."""

    def __init__(self, logger):
        self.solutions = OfflineSolutionDatabase()
        self.selected_guide: DiagnosticGuide | None = None
        self.live_cards: dict[str, dict[str, object]] = {}
        self.report_fields: dict[str, tk.Entry] = {}
        self.solution_texts: dict[str, tk.Text] = {}
        self.graph_axes = []
        super().__init__(logger)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=PRO["panel"])
        style.configure("Dark.TFrame", background=PRO["bg"])
        style.configure("Panel.TFrame", background=PRO["panel"])
        style.configure("TLabel", background=PRO["panel"], foreground=PRO["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PRO["panel"], foreground=PRO["muted"], font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=PRO["bg"], foreground=PRO["text"], font=("Segoe UI Semibold", 19))
        style.configure("TButton", background=PRO["panel3"], foreground=PRO["text"], bordercolor=PRO["border"], focusthickness=0, font=("Segoe UI Semibold", 9), padding=(12, 8))
        style.map("TButton", background=[("active", "#223140"), ("pressed", PRO["blue2"])], foreground=[("disabled", PRO["muted2"])])
        style.configure("Primary.TButton", background=PRO["blue"], foreground="white", bordercolor=PRO["blue"])
        style.map("Primary.TButton", background=[("active", PRO["blue2"]), ("disabled", "#31587A")])
        style.configure("Success.TButton", background=PRO["green"], foreground="white", bordercolor=PRO["green"])
        style.configure("Danger.TButton", background=PRO["red"], foreground="white", bordercolor=PRO["red"])
        style.configure("TEntry", fieldbackground=PRO["panel2"], foreground=PRO["text"], insertcolor=PRO["text"], bordercolor=PRO["border"], padding=7)
        style.configure("TCombobox", fieldbackground=PRO["panel2"], foreground=PRO["text"], arrowcolor=PRO["text"], bordercolor=PRO["border"], padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", PRO["panel2"]), ("disabled", PRO["panel"])] , foreground=[("readonly", PRO["text"]), ("disabled", PRO["muted2"])])
        style.configure("Treeview", background=PRO["panel"], fieldbackground=PRO["panel"], foreground=PRO["text"], rowheight=29, font=("Segoe UI", 9), bordercolor=PRO["border"])
        style.map("Treeview", background=[("selected", PRO["blue2"])], foreground=[("selected", "white")])
        style.configure("Treeview.Heading", background=PRO["panel3"], foreground=PRO["text"], font=("Segoe UI Semibold", 9), relief="flat")
        style.map("Treeview.Heading", background=[("active", "#223140")])
        style.configure("TNotebook", background=PRO["panel"], borderwidth=0)
        style.configure("TNotebook.Tab", background=PRO["panel3"], foreground=PRO["muted"], padding=(12, 8), font=("Segoe UI Semibold", 8))
        style.map("TNotebook.Tab", background=[("selected", PRO["blue2"])], foreground=[("selected", "white")])
        style.configure("Horizontal.TProgressbar", troughcolor=PRO["panel2"], background=PRO["blue"], bordercolor=PRO["panel2"])

    def _build_shell(self) -> None:
        self.configure(bg=PRO["bg"])
        self.geometry("1536x900")
        self.minsize(1180, 720)

        header = tk.Frame(self, bg=PRO["bg"], height=54, highlightbackground=PRO["border"], highlightthickness=0)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="SUPERSCAN 2.0", bg=PRO["bg"], fg=PRO["text"], font=("Segoe UI Black", 19)).pack(side="left", padx=(16, 10))
        tk.Label(header, text="DIAGNÓSTICO AUTOMOTRIZ PROFESIONAL", bg=PRO["bg"], fg=PRO["blue"], font=("Segoe UI Condensed Bold", 13)).pack(side="left")
        brand = tk.Frame(header, bg=PRO["bg"])
        brand.pack(side="left", padx=40)
        shield = tk.Canvas(brand, width=34, height=38, bg=PRO["bg"], highlightthickness=0)
        shield.pack(side="left")
        self._draw_shield(shield, 17, 20, 15)
        tk.Label(brand, text="AUTOGUARD", bg=PRO["bg"], fg=PRO["gold"], font=("Segoe UI Black", 14)).pack(side="left", padx=(5, 0))
        tk.Label(header, text=f"Versión {APP_VERSION}", bg=PRO["bg"], fg=PRO["muted2"], font=("Segoe UI", 8)).pack(side="right", padx=16)

        body = tk.Frame(self, bg=PRO["bg"])
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=PRO["sidebar"], width=165, highlightbackground=PRO["border"], highlightthickness=1)
        self.sidebar.pack(side="left", fill="y", padx=(8, 4), pady=(0, 8))
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="SUPERSCAN 2.0", bg=PRO["sidebar"], fg=PRO["blue"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=13, pady=(12, 8))

        self.nav_buttons = {}
        for label, page in NAV_ITEMS:
            button = tk.Button(
                self.sidebar,
                text=label,
                command=lambda p=page: self.show_page(p),
                anchor="w",
                relief="flat",
                bd=0,
                padx=12,
                pady=6,
                bg=PRO["sidebar"],
                fg="#D9E2EA",
                activebackground=PRO["blue2"],
                activeforeground="white",
                font=("Segoe UI Semibold", 8),
                cursor="hand2",
            )
            button.pack(fill="x", padx=5, pady=1)
            self.nav_buttons[page] = button

        status_box = tk.Frame(self.sidebar, bg=PRO["sidebar"])
        status_box.pack(side="bottom", fill="x", padx=12, pady=12)
        self.sidebar_status = tk.Label(status_box, text="● DESCONECTADO", bg=PRO["sidebar"], fg=PRO["red"], font=("Segoe UI Semibold", 8))
        self.sidebar_status.pack(anchor="w")
        tk.Label(status_box, text="Base offline activa", bg=PRO["sidebar"], fg=PRO["muted2"], font=("Segoe UI", 7)).pack(anchor="w", pady=(3, 0))

        self.main = tk.Frame(body, bg=PRO["bg"])
        self.main.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=(0, 8))
        self.topbar = tk.Frame(self.main, bg=PRO["panel"], height=48, highlightbackground=PRO["border"], highlightthickness=1)
        self.topbar.pack(fill="x", pady=(0, 6))
        self.topbar.pack_propagate(False)
        self.page_title = tk.Label(self.topbar, text="Inicio", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 14))
        self.page_title.pack(side="left", padx=16)
        self.status_text = tk.Label(self.topbar, text="Aplicación lista", bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 8))
        self.status_text.pack(side="right", padx=(6, 16))
        self.status_dot = tk.Label(self.topbar, text="●", bg=PRO["panel"], fg=PRO["red"], font=("Segoe UI", 12))
        self.status_dot.pack(side="right")

        self.content = tk.Frame(self.main, bg=PRO["bg"])
        self.content.pack(fill="both", expand=True)

    @staticmethod
    def _draw_shield(canvas: tk.Canvas, cx: float, cy: float, size: float) -> None:
        points = [
            cx, cy - size,
            cx + size * 0.9, cy - size * 0.55,
            cx + size * 0.72, cy + size * 0.55,
            cx, cy + size,
            cx - size * 0.72, cy + size * 0.55,
            cx - size * 0.9, cy - size * 0.55,
        ]
        canvas.create_polygon(points, fill=PRO["panel"], outline=PRO["gold"], width=2)
        canvas.create_text(cx, cy, text="AG", fill=PRO["gold"], font=("Segoe UI Black", max(7, int(size * 0.7))))

    def _build_pages(self) -> None:
        self._build_summary_page()
        self._build_connection_page()
        self._build_scan_page()
        self._build_dtc_page()
        self._build_live_page()
        self._build_graph_page()
        self._build_freeze_page()
        self._build_monitors_page()
        self._build_solution_page()
        self._build_database_page()
        self._build_report_page()
        self._build_history_page()
        self._build_configuration_page()
        self._build_console_page()

    def _new_page(self, name: str) -> tk.Frame:
        frame = tk.Frame(self.content, bg=PRO["bg"])
        self.pages[name] = frame
        return frame

    def _card(self, parent, *, padding: int = 12, bg: str | None = None) -> tk.Frame:
        bg = bg or PRO["panel"]
        card = tk.Frame(parent, bg=bg, highlightbackground=PRO["border"], highlightthickness=1)
        inner = tk.Frame(card, bg=bg)
        inner.pack(fill="both", expand=True, padx=padding, pady=padding)
        card.inner = inner  # type: ignore[attr-defined]
        return card

    def _section_header(self, parent, title: str, subtitle: str = "") -> None:
        tk.Label(parent, text=title.upper(), bg=PRO["bg"], fg=PRO["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
        if subtitle:
            tk.Label(parent, text=subtitle, bg=PRO["bg"], fg=PRO["muted"], font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 8))

    def _build_summary_page(self) -> None:
        page = self._new_page("Resumen")
        top = tk.Frame(page, bg=PRO["bg"])
        top.pack(fill="x")
        for column, weight in enumerate((4, 3, 3)):
            top.columnconfigure(column, weight=weight)

        vehicle = self._card(top)
        vehicle.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        connection = self._card(top)
        connection.grid(row=0, column=1, sticky="nsew", padx=4)
        status = self._card(top)
        status.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        tk.Label(vehicle.inner, text="VEHÍCULO", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        self.vehicle_subtitle = tk.Label(vehicle.inner, text="Esperando identificación OBD-II", bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 8))
        self.vehicle_subtitle.pack(anchor="w")
        self.logo_canvas = tk.Canvas(vehicle.inner, height=130, bg=PRO["panel"], highlightthickness=0)
        self.logo_canvas.pack(fill="x", pady=4)
        self.logo_canvas.bind("<Configure>", lambda _event: self._draw_autoguard_logo())
        self.summary_vin = tk.Label(vehicle.inner, text="VIN: —", bg=PRO["panel"], fg=PRO["text"], font=("Consolas", 8))
        self.summary_vin.pack(anchor="w")
        self.summary_protocol = tk.Label(vehicle.inner, text="Protocolo: —", bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 8), wraplength=430, justify="left")
        self.summary_protocol.pack(anchor="w", pady=(3, 0))

        tk.Label(connection.inner, text="CONEXIÓN", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        rows = [("Estado", "Desconectado"), ("Adaptador", "—"), ("Protocolo", "—"), ("Voltaje", "—"), ("PIDs soportados", "—")]
        self.dashboard_connection: dict[str, tk.Label] = {}
        for key, value in rows:
            row = tk.Frame(connection.inner, bg=PRO["panel"])
            row.pack(fill="x", pady=4)
            tk.Label(row, text=key, bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 8), width=14, anchor="w").pack(side="left")
            label = tk.Label(row, text=value, bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 8), anchor="w")
            label.pack(side="left", fill="x", expand=True)
            self.dashboard_connection[key] = label

        tk.Label(status.inner, text="ESTADO DEL DIAGNÓSTICO", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        self.health_indicator = tk.Canvas(status.inner, width=120, height=120, bg=PRO["panel"], highlightthickness=0)
        self.health_indicator.pack(pady=(5, 0))
        self.health_indicator.create_oval(10, 10, 110, 110, outline=PRO["border"], width=9)
        self.health_arc = self.health_indicator.create_arc(10, 10, 110, 110, start=90, extent=0, style="arc", outline=PRO["green"], width=9)
        self.health_text = self.health_indicator.create_text(60, 54, text="—", fill=PRO["text"], font=("Segoe UI Semibold", 21))
        self.health_label = self.health_indicator.create_text(60, 78, text="Sin escaneo", fill=PRO["muted"], font=("Segoe UI", 7))
        self.summary_dtc_count = tk.Label(status.inner, text="Códigos DTC: —", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 8))
        self.summary_dtc_count.pack()
        self.summary_pid_count = tk.Label(status.inner, text="PIDs disponibles: —", bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 8))
        self.summary_pid_count.pack()

        severity_row = tk.Frame(page, bg=PRO["bg"])
        severity_row.pack(fill="x", pady=7)
        self.severity_widgets: dict[str, tk.Label] = {}
        for index, (name, color) in enumerate((("DTC CONFIRMADOS", PRO["red"]), ("DTC PENDIENTES", PRO["orange"]), ("DTC PERMANENTES", "#D1A80D"), ("MONITORES", PRO["green"]))):
            severity_row.columnconfigure(index, weight=1)
            card = self._card(severity_row, padding=9, bg=color)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 3, 0 if index == 3 else 3))
            tk.Label(card.inner, text=name, bg=color, fg="white", font=("Segoe UI Semibold", 7)).pack(anchor="w")
            value = tk.Label(card.inner, text="—", bg=color, fg="white", font=("Segoe UI Semibold", 20))
            value.pack(anchor="w")
            self.severity_widgets[name] = value

        metric_row = tk.Frame(page, bg=PRO["bg"])
        metric_row.pack(fill="x")
        self.metric_widgets = {}
        metric_specs = [
            ("RPM motor", "rpm", PRO["blue"]),
            ("Temperatura refrigerante", "°C", PRO["green"]),
            ("Velocidad", "km/h", PRO["cyan"]),
            ("Carga calculada", "%", PRO["orange"]),
            ("Ajuste combustible corto B1", "%", PRO["blue"]),
            ("Ajuste combustible largo B1", "%", PRO["orange"]),
            ("Caudal de combustible", "L/h", PRO["purple"]),
            ("Nivel de combustible", "%", PRO["green"]),
            ("Voltaje adaptador", "V", PRO["gold"]),
        ]
        for index, (name, unit, color) in enumerate(metric_specs):
            metric_row.columnconfigure(index, weight=1)
            card = self._card(metric_row, padding=7)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 2, 0 if index == len(metric_specs) - 1 else 2))
            tk.Label(card.inner, text=name, bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 6), wraplength=100).pack(anchor="w")
            value = tk.Label(card.inner, text="—", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 13))
            value.pack(anchor="w")
            tk.Label(card.inner, text=unit, bg=PRO["panel"], fg=color, font=("Segoe UI", 7)).pack(anchor="w")
            self.metric_widgets[name] = value

        actions = self._card(page, padding=8)
        actions.pack(fill="x", pady=(7, 0))
        for text, target, style_name in (("Códigos DTC", "Códigos DTC", "TButton"), ("Datos en Vivo", "Datos en vivo", "TButton"), ("Gráficos HD", "Gráficos", "TButton"), ("Solución Guiada", "Solución Guiada", "TButton"), ("Informes", "Informe", "Primary.TButton")):
            ttk.Button(actions.inner, text=text, style=style_name, command=lambda page_name=target: self.show_page(page_name)).pack(side="left", padx=4)

    def _draw_autoguard_logo(self) -> None:
        canvas = self.logo_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        cx, cy = width / 2, 62
        size = 49
        points = [cx, cy - size, cx + size * 0.9, cy - size * 0.55, cx + size * 0.72, cy + size * 0.55, cx, cy + size, cx - size * 0.72, cy + size * 0.55, cx - size * 0.9, cy - size * 0.55]
        canvas.create_polygon(points, fill=PRO["panel2"], outline=PRO["gold"], width=4)
        canvas.create_text(cx, cy - 4, text="AG", fill=PRO["gold"], font=("Segoe UI Black", 29))
        canvas.create_text(cx, cy + 31, text="AUTOGUARD", fill=PRO["gold"], font=("Segoe UI Black", 9))
        canvas.create_text(cx, cy + 45, text="DIAGNÓSTICO INTELIGENTE", fill=PRO["text"], font=("Segoe UI", 5))

    def _dark_text(self, parent, *, height=10, font=("Consolas", 9)) -> tk.Text:
        return tk.Text(parent, height=height, wrap="word", bg=PRO["panel2"], fg=PRO["text"], insertbackground=PRO["text"], relief="flat", font=font, padx=10, pady=10, selectbackground=PRO["blue2"])

    def _build_connection_page(self) -> None:
        page = self._new_page("Conexión")
        self._section_header(page, "Conexión OBD-II", "COM, Wi-Fi y simulador profesional integrado")
        form_card = self._card(page)
        form_card.pack(fill="x")
        form = form_card.inner
        form.columnconfigure(1, weight=1)
        fields = [("Modo de conexión", 0), ("Puerto serial", 1), ("Velocidad", 2), ("Dirección Wi-Fi", 3), ("Puerto TCP", 4)]
        for label, row in fields:
            tk.Label(form, text=label, bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        self.connection_mode = ttk.Combobox(form, values=["Simulador", "COM", "WiFi"], state="readonly")
        self.connection_mode.set("Simulador")
        self.connection_mode.grid(row=0, column=1, sticky="ew", pady=5)
        self.connection_mode.bind("<<ComboboxSelected>>", lambda _e: self._update_connection_fields())
        self.com_port = ttk.Combobox(form, values=available_serial_ports(), state="readonly")
        self.com_port.grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Button(form, text="Actualizar puertos", command=self.refresh_ports).grid(row=1, column=2, padx=(8, 0))
        self.baudrate = ttk.Combobox(form, values=[9600, 38400, 57600, 115200], state="readonly")
        self.baudrate.set("38400")
        self.baudrate.grid(row=2, column=1, sticky="ew", pady=5)
        self.wifi_host = ttk.Entry(form)
        self.wifi_host.insert(0, "192.168.0.10")
        self.wifi_host.grid(row=3, column=1, sticky="ew", pady=5)
        self.wifi_port = ttk.Entry(form)
        self.wifi_port.insert(0, "35000")
        self.wifi_port.grid(row=4, column=1, sticky="ew", pady=5)
        controls = tk.Frame(form, bg=PRO["panel"])
        controls.grid(row=5, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.connect_button = ttk.Button(controls, text="Conectar y detectar protocolo", style="Primary.TButton", command=self.connect_selected)
        self.connect_button.pack(side="left")
        self.disconnect_button = ttk.Button(controls, text="Desconectar", command=self.disconnect, state="disabled")
        self.disconnect_button.pack(side="left", padx=8)
        info = self._card(page)
        info.pack(fill="both", expand=True, pady=(7, 0))
        tk.Label(info.inner, text="ESTADO DE COMUNICACIÓN", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
        self.connection_info = self._dark_text(info.inner, height=12)
        self.connection_info.pack(fill="both", expand=True, pady=(6, 0))
        self.connection_info.insert("end", "Seleccione un modo y presione Conectar.\n")
        self.connection_info.configure(state="disabled")
        self._update_connection_fields()

    def _build_scan_page(self) -> None:
        page = self._new_page("Escaneo")
        self._section_header(page, "Diagnóstico automático", "Identificación, protocolo, PIDs, DTC y evaluación inicial")
        controls = self._card(page)
        controls.pack(fill="x")
        self.scan_button = ttk.Button(controls.inner, text="Iniciar diagnóstico completo", style="Primary.TButton", command=self.start_scan)
        self.scan_button.pack(side="left")
        self.scan_progress = ttk.Progressbar(controls.inner, mode="indeterminate", length=250)
        self.scan_progress.pack(side="left", padx=12)
        self.scan_state = tk.Label(controls.inner, text="En espera", bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 9))
        self.scan_state.pack(side="left")
        result = self._card(page)
        result.pack(fill="both", expand=True, pady=(7, 0))
        self.scan_text = self._dark_text(result.inner, height=25)
        self.scan_text.pack(fill="both", expand=True)
        self.scan_text.insert("end", "Conecte el adaptador y ejecute el diagnóstico.\n")
        self.scan_text.configure(state="disabled")

    def _build_dtc_page(self) -> None:
        page = self._new_page("Códigos DTC")
        self._section_header(page, "Códigos DTC", "Descripción, severidad y solución guiada offline")
        bar = tk.Frame(page, bg=PRO["bg"])
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="Leer códigos", style="Primary.TButton", command=self.refresh_dtcs).pack(side="left")
        ttk.Button(bar, text="Borrar códigos", style="Danger.TButton", command=self.clear_dtcs).pack(side="left", padx=6)
        self.dtc_summary_label = tk.Label(bar, text="Sin lectura", bg=PRO["bg"], fg=PRO["muted"], font=("Segoe UI", 8))
        self.dtc_summary_label.pack(side="right")

        split = tk.PanedWindow(page, orient="horizontal", bg=PRO["bg"], sashwidth=5, sashrelief="flat", bd=0)
        split.pack(fill="both", expand=True)
        left = self._card(split, padding=6)
        right = self._card(split, padding=8)
        split.add(left, minsize=520)
        split.add(right, minsize=430)
        columns = ("code", "status", "severity", "description")
        self.dtc_tree = ttk.Treeview(left.inner, columns=columns, show="headings")
        for col, title, width in (("code", "Código", 75), ("status", "Estado", 145), ("severity", "Severidad", 80), ("description", "Descripción", 400)):
            self.dtc_tree.heading(col, text=title)
            self.dtc_tree.column(col, width=width, anchor="center" if col != "description" else "w")
        self.dtc_tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(left.inner, orient="vertical", command=self.dtc_tree.yview)
        scroll.pack(side="right", fill="y")
        self.dtc_tree.configure(yscrollcommand=scroll.set)
        for severity, color in SEVERITY.items():
            self.dtc_tree.tag_configure(severity, foreground=color)
        self.dtc_tree.bind("<<TreeviewSelect>>", self._on_dtc_selected)

        tk.Label(right.inner, text="SOLUCIÓN GUIADA", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        self.dtc_solution_title = tk.Label(right.inner, text="Seleccione un código", bg=PRO["panel"], fg=PRO["blue"], font=("Segoe UI Semibold", 11), wraplength=520, justify="left")
        self.dtc_solution_title.pack(anchor="w", pady=(3, 5))
        self.dtc_solution_preview = self._dark_text(right.inner, height=20, font=("Segoe UI", 9))
        self.dtc_solution_preview.pack(fill="both", expand=True)
        self.dtc_solution_preview.insert("end", "La ficha mostrará causas, pasos, herramientas y validación.\n")
        self.dtc_solution_preview.configure(state="disabled")
        ttk.Button(right.inner, text="Abrir solución completa", style="Primary.TButton", command=lambda: self.show_page("Solución Guiada")).pack(anchor="e", pady=(6, 0))

    def _metric_card(self, parent, name: str, unit: str, color: str, row: int, column: int) -> None:
        card = self._card(parent, padding=8)
        card.grid(row=row, column=column, sticky="nsew", padx=3, pady=3)
        tk.Label(card.inner, text=name, bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 7), wraplength=155).pack(anchor="w")
        value = tk.Label(card.inner, text="—", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 17))
        value.pack(anchor="w")
        tk.Label(card.inner, text=unit, bg=PRO["panel"], fg=color, font=("Segoe UI", 7)).pack(anchor="w")
        spark = tk.Canvas(card.inner, height=28, bg=PRO["panel"], highlightthickness=0)
        spark.pack(fill="x", pady=(3, 0))
        self.live_cards[name] = {"value": value, "canvas": spark, "color": color}

    def _build_live_page(self) -> None:
        page = self._new_page("Datos en vivo")
        self._section_header(page, "Datos en vivo", "Tarjetas dinámicas, estado de señal y tendencias instantáneas")
        bar = tk.Frame(page, bg=PRO["bg"])
        bar.pack(fill="x", pady=(0, 5))
        self.live_toggle_button = ttk.Button(bar, text="Iniciar actualización", style="Primary.TButton", command=self.toggle_live)
        self.live_toggle_button.pack(side="left")
        self.live_status_label = tk.Label(bar, text="Detenido", bg=PRO["bg"], fg=PRO["muted"], font=("Segoe UI", 8))
        self.live_status_label.pack(side="left", padx=10)
        cards = tk.Frame(page, bg=PRO["bg"])
        cards.pack(fill="both", expand=True)
        for column in range(4):
            cards.columnconfigure(column, weight=1)
        for row in range(3):
            cards.rowconfigure(row, weight=1)
        card_specs = [
            ("RPM motor", "rpm", PRO["green"]), ("Temperatura refrigerante", "°C", PRO["green"]), ("Velocidad", "km/h", PRO["blue"]), ("Carga calculada", "%", PRO["green"]),
            ("Ajuste combustible corto B1", "%", PRO["blue"]), ("Ajuste combustible largo B1", "%", PRO["orange"]), ("Presión MAP", "kPa", PRO["green"]), ("Flujo de aire MAF", "g/s", PRO["green"]),
            ("Nivel de combustible", "%", PRO["green"]), ("Caudal de combustible", "L/h", PRO["purple"]), ("Voltaje adaptador", "V", PRO["gold"]), ("Temperatura admisión", "°C", PRO["cyan"]),
        ]
        for index, spec in enumerate(card_specs):
            self._metric_card(cards, *spec, row=index // 4, column=index % 4)
        self.live_tree = ttk.Treeview(page, columns=("name", "value", "unit", "state"), show="headings", height=1)
        for col, title in (("name", "Parámetro"), ("value", "Valor"), ("unit", "Unidad"), ("state", "Estado")):
            self.live_tree.heading(col, text=title)
        # Se mantiene para compatibilidad del motor; las tarjetas son la visualización principal.

    def _build_graph_page(self) -> None:
        page = self._new_page("Gráficos")
        self._section_header(page, "Gráficos HD", "Múltiples PIDs en tiempo real, captura y comparación")
        bar = tk.Frame(page, bg=PRO["bg"])
        bar.pack(fill="x", pady=(0, 5))
        names = [PID_DEFINITIONS[cmd][0] for cmd in LIVE_PID_ORDER] + ["Voltaje adaptador"]
        self.graph_parameter = ttk.Combobox(bar, values=names, state="readonly", width=34)
        self.graph_parameter.set("RPM motor")
        self.graph_parameter.pack(side="left")
        ttk.Button(bar, text="Actualizar", command=self.update_graph).pack(side="left", padx=5)
        ttk.Button(bar, text="Limpiar historial", command=self.clear_graph_history).pack(side="left")
        card = self._card(page, padding=5)
        card.pack(fill="both", expand=True)
        self.figure = Figure(figsize=(11, 7), dpi=110, facecolor=PRO["panel"])
        self.graph_axes = [self.figure.add_subplot(5, 1, index + 1) for index in range(5)]
        self.axes = self.graph_axes[0]
        self.graph_canvas = FigureCanvasTkAgg(self.figure, master=card.inner)
        self.graph_canvas.get_tk_widget().configure(bg=PRO["panel"], highlightthickness=0)
        self.graph_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.update_graph()

    def _build_freeze_page(self) -> None:
        page = self._new_page("Freeze Frame")
        self._section_header(page, "Freeze Frame", "Condiciones registradas por la ECU en el momento de la falla")
        ttk.Button(page, text="Leer Freeze Frame", style="Primary.TButton", command=self.read_freeze_frame).pack(anchor="w", pady=(0, 6))
        card = self._card(page, padding=6)
        card.pack(fill="both", expand=True)
        self.freeze_tree = ttk.Treeview(card.inner, columns=("parameter", "value", "unit"), show="headings")
        for col, title, width in (("parameter", "Parámetro", 430), ("value", "Valor", 230), ("unit", "Unidad", 170)):
            self.freeze_tree.heading(col, text=title)
            self.freeze_tree.column(col, width=width, anchor="center" if col != "parameter" else "w")
        self.freeze_tree.pack(fill="both", expand=True)

    def _build_monitors_page(self) -> None:
        page = self._new_page("Monitores")
        self._section_header(page, "Monitores OBD-II", "MIL, readiness y estado de sistemas continuos")
        ttk.Button(page, text="Actualizar monitores", style="Primary.TButton", command=self.read_monitors).pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(page, bg=PRO["bg"])
        grid.pack(fill="both", expand=True)
        self.monitor_labels = {}
        specs = (("mil", "Luz MIL"), ("dtc_count", "Cantidad DTC"), ("misfire_available", "Monitor de encendido"), ("fuel_available", "Sistema de combustible"), ("components_available", "Componentes"), ("raw", "Respuesta PID 0101"))
        for index, (key, title) in enumerate(specs):
            grid.columnconfigure(index % 3, weight=1)
            grid.rowconfigure(index // 3, weight=1)
            card = self._card(grid)
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=3, pady=3)
            tk.Label(card.inner, text=title.upper(), bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w")
            label = tk.Label(card.inner, text="—", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 18), wraplength=300)
            label.pack(anchor="w", pady=10)
            self.monitor_labels[key] = label

    def _build_solution_page(self) -> None:
        page = self._new_page("Solución Guiada")
        self._section_header(page, "Solución guiada", "Causas, pruebas, proceso paso a paso y validación por código")
        header = self._card(page, padding=8)
        header.pack(fill="x", pady=(0, 6))
        self.guide_header = tk.Label(header.inner, text="Seleccione un código DTC en la página Códigos DTC", bg=PRO["panel"], fg=PRO["blue"], font=("Segoe UI Semibold", 12), wraplength=1000, justify="left")
        self.guide_header.pack(anchor="w")
        self.guide_severity = tk.Label(header.inner, text="", bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI Semibold", 9))
        self.guide_severity.pack(anchor="w", pady=(2, 0))
        notebook = ttk.Notebook(page)
        notebook.pack(fill="both", expand=True)
        for key, title in (("Resumen", "Resumen"), ("Causas", "Causas"), ("Plan", "Plan de Acción"), ("Herramientas", "Pruebas y Herramientas"), ("Validación", "Validación")):
            frame = tk.Frame(notebook, bg=PRO["panel"])
            notebook.add(frame, text=title)
            text = self._dark_text(frame, height=25, font=("Segoe UI", 10))
            text.pack(fill="both", expand=True, padx=6, pady=6)
            text.configure(state="disabled")
            self.solution_texts[key] = text

    def _build_database_page(self) -> None:
        page = self._new_page("Base DTC")
        self._section_header(page, "Base de datos offline", f"{TOTAL_DTC_RECORDS:,} códigos y {self.solutions.count():,} planes de solución locales".replace(",", "."))
        bar = tk.Frame(page, bg=PRO["bg"])
        bar.pack(fill="x", pady=(0, 6))
        self.db_search_entry = ttk.Entry(bar)
        self.db_search_entry.pack(side="left", fill="x", expand=True)
        self.db_search_entry.bind("<Return>", lambda _e: self.search_database())
        ttk.Button(bar, text="Buscar", style="Primary.TButton", command=self.search_database).pack(side="left", padx=5)
        self.db_count_label = tk.Label(bar, text="", bg=PRO["bg"], fg=PRO["muted"], font=("Segoe UI", 8))
        self.db_count_label.pack(side="right")
        card = self._card(page, padding=5)
        card.pack(fill="both", expand=True)
        self.db_tree = ttk.Treeview(card.inner, columns=("code", "system", "scope", "severity", "description"), show="headings")
        for col, title, width in (("code", "Código", 75), ("system", "Sistema", 120), ("scope", "Alcance", 90), ("severity", "Severidad", 80), ("description", "Descripción", 680)):
            self.db_tree.heading(col, text=title)
            self.db_tree.column(col, width=width, anchor="center" if col != "description" else "w")
        self.db_tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(card.inner, orient="vertical", command=self.db_tree.yview)
        scroll.pack(side="right", fill="y")
        self.db_tree.configure(yscrollcommand=scroll.set)
        self.search_database()

    def _build_report_page(self) -> None:
        page = self._new_page("Informe")
        self._section_header(page, "Informe profesional", "PDF multipágina con gráficos, DTC, severidad, planes de acción y checklist")
        split = tk.Frame(page, bg=PRO["bg"])
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=2)
        split.columnconfigure(1, weight=3)
        form_card = self._card(split)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        preview = self._card(split)
        preview.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        tk.Label(form_card.inner, text="DATOS DEL INFORME", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w", pady=(0, 6))
        for field, label in (("tecnico", "Técnico"), ("cliente", "Cliente"), ("vehiculo", "Vehículo"), ("patente", "Patente"), ("kilometraje", "Kilometraje")):
            tk.Label(form_card.inner, text=label, bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 8)).pack(anchor="w")
            entry = ttk.Entry(form_card.inner)
            entry.pack(fill="x", pady=(2, 6))
            if field == "tecnico":
                entry.insert(0, "Esteban Cortez")
            self.report_fields[field] = entry
        ttk.Button(form_card.inner, text="Generar informe profesional", style="Primary.TButton", command=self.generate_report).pack(fill="x", pady=(6, 3))
        ttk.Button(form_card.inner, text="Abrir carpeta de informes", command=self.open_report_folder).pack(fill="x")
        self.report_status = tk.Label(form_card.inner, text=str(REPORT_DIR), bg=PRO["panel"], fg=PRO["muted"], font=("Segoe UI", 7), wraplength=330, justify="left")
        self.report_status.pack(anchor="w", pady=(8, 0))
        tk.Label(preview.inner, text="CONTENIDO DEL INFORME", bg=PRO["panel"], fg=PRO["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        preview_text = self._dark_text(preview.inner, height=28, font=("Segoe UI", 9))
        preview_text.pack(fill="both", expand=True, pady=(6, 0))
        preview_text.insert("end", """PÁGINA 1 · Identificación y resumen ejecutivo
• Datos de vehículo, VIN, protocolo y técnico
• Estado general y prioridad
• Gráfico de distribución de severidad
• Tabla de códigos encontrados

PÁGINA 2 · Datos en vivo y gráficos HD
• Valores actuales, mínimos y máximos
• RPM, temperaturas, ajustes de combustible
• Caudal y nivel de combustible
• Plan de acción general

PÁGINAS SIGUIENTES · Solución por código
• Síntomas y causas probables
• Proceso de diagnóstico paso a paso
• Herramientas requeridas
• Validación de reparación y seguridad

CIERRE · Checklist técnico y alcance del informe
""")
        preview_text.configure(state="disabled")

    def _build_history_page(self) -> None:
        page = self._new_page("Historial")
        self._section_header(page, "Historial", "Registros y documentos generados en el equipo")
        card = self._card(page)
        card.pack(fill="both", expand=True)
        self.history_text = self._dark_text(card.inner, height=25, font=("Segoe UI", 9))
        self.history_text.pack(fill="both", expand=True)
        self._refresh_history()

    def _refresh_history(self) -> None:
        if not hasattr(self, "history_text"):
            return
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(REPORT_DIR.glob("*.pdf"), key=lambda path: path.stat().st_mtime, reverse=True)[:100]
        lines = ["INFORMES DISPONIBLES", "=" * 70]
        lines.extend(f"{index:03d}  {path.name}" for index, path in enumerate(files, start=1))
        if not files:
            lines.append("No existen informes generados.")
        self._set_text_widget(self.history_text, "\n".join(lines) + "\n")

    def _build_configuration_page(self) -> None:
        page = self._new_page("Configuración")
        self._section_header(page, "Configuración", "Parámetros locales de la aplicación")
        card = self._card(page)
        card.pack(fill="x")
        items = [
            ("Interfaz", "Profesional oscura AutoGuard"),
            ("Base DTC", f"{TOTAL_DTC_RECORDS:,} registros".replace(",", ".")),
            ("Base de soluciones", f"{self.solutions.count():,} procedimientos".replace(",", ".")),
            ("Informes", str(REPORT_DIR)),
            ("Registro técnico", str(LOG_FILE)),
        ]
        for title, value in items:
            row = tk.Frame(card.inner, bg=PRO["panel"])
            row.pack(fill="x", pady=5)
            tk.Label(row, text=title, bg=PRO["panel"], fg=PRO["muted"], width=22, anchor="w", font=("Segoe UI", 9)).pack(side="left")
            tk.Label(row, text=value, bg=PRO["panel"], fg=PRO["text"], anchor="w", font=("Segoe UI Semibold", 9), wraplength=850).pack(side="left", fill="x", expand=True)

    def _build_console_page(self) -> None:
        page = self._new_page("Consola")
        self._section_header(page, "Consola técnica", "Comandos TX/RX y eventos de diagnóstico")
        bar = tk.Frame(page, bg=PRO["bg"])
        bar.pack(fill="x", pady=(0, 5))
        ttk.Button(bar, text="Limpiar", command=self.clear_console).pack(side="left")
        ttk.Button(bar, text="Abrir registro", command=self.open_log).pack(side="left", padx=5)
        self.console = self._dark_text(page, height=30)
        self.console.pack(fill="both", expand=True)
        self.console.insert("end", f"{APP_NAME} · Consola técnica profesional\n")
        self.console.configure(state="disabled")

    def show_page(self, name: str) -> None:
        if name not in self.pages:
            return
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        display = next((label for label, page in NAV_ITEMS if page == name), name)
        self.page_title.configure(text=display)
        for page_name, button in self.nav_buttons.items():
            button.configure(bg=PRO["blue2"] if page_name == name else PRO["sidebar"], fg="white" if page_name == name else "#D9E2EA")
        if name == "Gráficos":
            self.update_graph()
        elif name == "Solución Guiada" and self.selected_guide:
            self._render_solution(self.selected_guide)
        elif name == "Historial":
            self._refresh_history()

    def _set_status(self, text: str, connected: bool | None = None) -> None:
        self.status_text.configure(text=text)
        if connected is not None:
            color = PRO["green"] if connected else PRO["red"]
            self.status_dot.configure(fg=color)
            self.sidebar_status.configure(text="● CONECTADO" if connected else "● DESCONECTADO", fg=color)
            if "Estado" in getattr(self, "dashboard_connection", {}):
                self.dashboard_connection["Estado"].configure(text="Conectado" if connected else "Desconectado", fg=color)

    def _on_connected(self, payload: object) -> None:
        super()._on_connected(payload)
        if self.client:
            for key, value in (("Estado", "Conectado"), ("Adaptador", self.client.adapter_name), ("Protocolo", self.client.protocol_name)):
                self.dashboard_connection[key].configure(text=value, fg=PRO["green"] if key == "Estado" else PRO["text"])

    def _on_scan_complete(self, payload: object) -> None:
        super()._on_scan_complete(payload)
        if isinstance(payload, VehicleScan):
            self.dashboard_connection["PIDs soportados"].configure(text=f"{len(payload.supported_pids)}")
            confirmed = sum(item.status.startswith("Confirmado") for item in payload.dtcs)
            pending = sum(item.status.startswith("Pendiente") for item in payload.dtcs)
            permanent = sum(item.status.startswith("Permanente") for item in payload.dtcs)
            self.severity_widgets["DTC CONFIRMADOS"].configure(text=str(confirmed))
            self.severity_widgets["DTC PENDIENTES"].configure(text=str(pending))
            self.severity_widgets["DTC PERMANENTES"].configure(text=str(permanent))
            self.severity_widgets["MONITORES"].configure(text="OBD")

    def _populate_dtc_tree(self, dtcs: list[DTCResult]) -> None:
        for item in self.dtc_tree.get_children():
            self.dtc_tree.delete(item)
        for dtc in dtcs:
            record = self.db.lookup(dtc.code)
            guide = self.solutions.lookup(dtc.code, record.description, record.system)
            self.dtc_tree.insert("", "end", iid=f"dtc-{len(self.dtc_tree.get_children())}", values=(dtc.code, dtc.status, guide.severity, record.description), tags=(guide.severity,))
        self.dtc_summary_label.configure(text=f"{len(dtcs)} códigos encontrados")
        self.summary_dtc_count.configure(text=f"Códigos DTC: {len(dtcs)}")
        if dtcs:
            first = self.dtc_tree.get_children()[0]
            self.dtc_tree.selection_set(first)
            self.dtc_tree.focus(first)
            self._on_dtc_selected()

    def _on_dtc_selected(self, _event=None) -> None:
        selected = self.dtc_tree.selection()
        if not selected:
            return
        values = self.dtc_tree.item(selected[0], "values")
        if not values:
            return
        code = str(values[0])
        record = self.db.lookup(code)
        guide = self.solutions.lookup(code, record.description, record.system)
        self.selected_guide = guide
        self.dtc_solution_title.configure(text=f"{code} · {record.description}", fg=SEVERITY.get(guide.severity, PRO["blue"]))
        preview = [guide.summary, "", "CAUSAS PROBABLES"]
        preview.extend(f"• {item}" for item in guide.causes[:5])
        preview.extend(["", "PRIMEROS PASOS"])
        preview.extend(f"{index}. {item}" for index, item in enumerate(guide.steps[:6], start=1))
        self._set_text_widget(self.dtc_solution_preview, "\n".join(preview) + "\n")
        self._render_solution(guide)

    def _render_solution(self, guide: DiagnosticGuide) -> None:
        record = self.db.lookup(guide.code)
        self.guide_header.configure(text=f"{guide.code} · {record.description}", fg=SEVERITY.get(guide.severity, PRO["blue"]))
        self.guide_severity.configure(text=f"SEVERIDAD {guide.severity} · {guide.source_scope}", fg=SEVERITY.get(guide.severity, PRO["muted"]))
        contents = {
            "Resumen": guide.summary + "\n\nSÍNTOMAS PROBABLES\n" + "\n".join(f"• {item}" for item in guide.symptoms) + f"\n\nSEGURIDAD\n{guide.safety_notice}",
            "Causas": "CAUSAS PROBABLES\n\n" + "\n".join(f"{index}. {item}" for index, item in enumerate(guide.causes, start=1)),
            "Plan": "PROCESO PASO A PASO\n\n" + "\n\n".join(f"PASO {index}\n{item}" for index, item in enumerate(guide.steps, start=1)),
            "Herramientas": "HERRAMIENTAS Y PRUEBAS\n\n" + "\n".join(f"• {item}" for item in guide.tools) + "\n\nUsar diagramas y especificaciones del fabricante cuando la medición requiera valores exactos.",
            "Validación": "VALIDACIÓN DE LA REPARACIÓN\n\n" + "\n".join(f"☑ {item}" for item in guide.validation) + "\n\nNo cerrar el diagnóstico únicamente porque el DTC pudo borrarse.",
        }
        for key, text in contents.items():
            self._set_text_widget(self.solution_texts[key], text + "\n")

    def _populate_live_tree(self, data: dict[str, tuple[float | None, str]]) -> None:
        existing = {self.live_tree.set(item, "name"): item for item in self.live_tree.get_children()}
        for name, (value, unit) in data.items():
            formatted = "—" if value is None else f"{value:.2f}"
            state = "Disponible" if value is not None else "Sin respuesta"
            if name in existing:
                self.live_tree.item(existing[name], values=(name, formatted, unit, state))
            else:
                self.live_tree.insert("", "end", values=(name, formatted, unit, state))
            card = self.live_cards.get(name)
            if card:
                label = card["value"]
                if isinstance(label, tk.Label):
                    label.configure(text=formatted)
                canvas = card["canvas"]
                if isinstance(canvas, tk.Canvas):
                    self._draw_sparkline(canvas, name, str(card["color"]))

    def _draw_sparkline(self, canvas: tk.Canvas, name: str, color: str) -> None:
        canvas.delete("all")
        points = list(self.history.get(name, []))[-45:]
        width = max(canvas.winfo_width(), 120)
        height = max(canvas.winfo_height(), 28)
        canvas.create_line(0, height - 2, width, height - 2, fill=PRO["border"])
        if len(points) < 2:
            return
        values = [value for _, value in points]
        low, high = min(values), max(values)
        span = max(high - low, 1e-6)
        coords = []
        for index, value in enumerate(values):
            x = index * (width - 4) / max(len(values) - 1, 1) + 2
            y = height - 3 - (value - low) * (height - 8) / span
            coords.extend((x, y))
        canvas.create_line(*coords, fill=color, width=1.5, smooth=True)

    def _update_summary_metrics(self, data: dict[str, tuple[float | None, str]]) -> None:
        for name, widget in self.metric_widgets.items():
            value = data.get(name, (None, ""))[0]
            widget.configure(text="—" if value is None else f"{value:.2f}")
        voltage = data.get("Voltaje adaptador", (None, ""))[0]
        if voltage is not None and "Voltaje" in self.dashboard_connection:
            self.dashboard_connection["Voltaje"].configure(text=f"{voltage:.2f} V")

    def update_graph(self) -> None:
        if not self.graph_axes:
            return
        preferred = [self.graph_parameter.get() or "RPM motor", "Temperatura refrigerante", "Ajuste combustible corto B1", "Ajuste combustible largo B1", "Caudal de combustible"]
        colors = [PRO["blue"], PRO["green"], PRO["blue"], PRO["orange"], PRO["purple"]]
        for axis, name, color in zip(self.graph_axes, preferred, colors):
            axis.clear()
            axis.set_facecolor(PRO["panel"])
            axis.tick_params(colors=PRO["muted"], labelsize=7)
            for spine in axis.spines.values():
                spine.set_color(PRO["border"])
            axis.grid(True, alpha=0.18, color=PRO["muted"])
            axis.set_ylabel(name, color=PRO["text"], fontsize=7)
            points = list(self.history.get(name, []))
            if points:
                xs, ys = zip(*points)
                axis.plot(xs, ys, color=color, linewidth=1.4)
                axis.fill_between(xs, ys, color=color, alpha=0.08)
                axis.text(0.99, 0.75, f"{ys[-1]:.2f}", transform=axis.transAxes, ha="right", color=PRO["text"], fontsize=8, fontweight="bold")
            else:
                axis.text(0.5, 0.5, "Sin datos", transform=axis.transAxes, ha="center", va="center", color=PRO["muted"], fontsize=8)
        self.graph_axes[-1].set_xlabel("Tiempo de sesión (s)", color=PRO["muted"], fontsize=7)
        self.figure.tight_layout(pad=0.8)
        self.graph_canvas.draw_idle()

    def search_database(self) -> None:
        query = self.db_search_entry.get() if hasattr(self, "db_search_entry") else ""
        rows = self.db.search(query, limit=500)
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        for record in rows:
            guide = self.solutions.lookup(record.code, record.description, record.system)
            self.db_tree.insert("", "end", values=(record.code, record.system, record.scope, guide.severity, record.description))
        self.db_count_label.configure(text=f"{len(rows)} resultados · {self.db.count():,} códigos · {self.solutions.count():,} soluciones".replace(",", "."))

    def generate_report(self) -> None:
        self._set_status("Generando informe profesional...")
        self.report_status.configure(text="Generando PDF con gráficos y planes de acción...", fg=PRO["muted"])
        metadata = {key: entry.get().strip() for key, entry in self.report_fields.items()}

        def operation() -> Path:
            return generate_professional_report(
                self.scan_result,
                self.current_dtcs,
                self.current_live,
                self.history,
                self.db,
                self.solutions,
                metadata,
            )

        self._run_worker(operation, "report")

    def _on_report(self, payload: object) -> None:
        super()._on_report(payload)
        self._refresh_history()

    def disconnect(self) -> None:
        super().disconnect()
        for key, value in (("Estado", "Desconectado"), ("Adaptador", "—"), ("Protocolo", "—"), ("Voltaje", "—"), ("PIDs soportados", "—")):
            if key in self.dashboard_connection:
                self.dashboard_connection[key].configure(text=value, fg=PRO["red"] if key == "Estado" else PRO["text"])
