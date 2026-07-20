from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

import premium_app as premium_module
from core import PID_DEFINITIONS
from dtc_database import resource_path
from final_dios_app import DEFAULT_LIVE_PIDS, SENSOR_SYSTEMS
from final_widgets import SensorDetailWindow, format_value
from god_premium_app import GodPremiumApp
from premium_app import (
    APP_AUTHOR,
    BG,
    GREEN,
    MUTED,
    ORANGE,
    ORANGE_DARK,
    ORANGE_LIGHT,
    PANEL,
    PANEL_2,
    RED,
    TEXT,
    YELLOW,
)
from premium_gauges import RealisticGauge

NAV_VERSION = "6.2.2 NIVEL DIOS PREMIUM"
NAV_BUILD = "Navegación por páginas · Modo escáner · Interfaz Full HD"

premium_module.APP_VERSION = NAV_VERSION
premium_module.APP_BUILD = NAV_BUILD


class NavigationPremiumApp(GodPremiumApp):
    """Final workshop interface with separated pages and large navigation."""

    def __init__(self) -> None:
        self.fullscreen_enabled = False
        self.scanner_mode_enabled = False
        self.dashboard_items: dict[int, str] = {}
        super().__init__()
        self.title(f"AUTOGUARD SCAN DIOS v{NAV_VERSION}")
        self.geometry("1600x920")
        self.minsize(1280, 720)
        self.bind("<F11>", lambda _event: self._toggle_fullscreen())
        self.bind("<Escape>", lambda _event: self._exit_fullscreen())
        self.bind("<Control-m>", lambda _event: self._toggle_scanner_mode())
        self.after(140, lambda: self._show_page("Inicio"))

    # ------------------------------------------------------------------
    # Shell, sidebar and header
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        self.sidebar.configure(
            bg="#060A0F",
            width=250,
            highlightbackground="#2C3946",
            highlightthickness=1,
        )
        self.sidebar.pack_propagate(False)
        for child in self.sidebar.winfo_children():
            child.destroy()

        brand = tk.Frame(self.sidebar, bg="#060A0F")
        brand.pack(fill="x", pady=(10, 10))
        self.sidebar_brand = self._load_brand((210, 102))
        if self.sidebar_brand is not None:
            tk.Label(brand, image=self.sidebar_brand, bg="#060A0F").pack()
        else:
            tk.Label(brand, text="AUTO GUARD SERVICE", bg="#060A0F", fg=ORANGE, font=("Segoe UI", 15, "bold")).pack(pady=16)
        tk.Label(brand, text="SCAN DIOS v6.2", bg="#060A0F", fg=TEXT, font=("Segoe UI", 11, "bold")).pack(pady=(4, 0))

        tk.Frame(self.sidebar, bg="#273543", height=1).pack(fill="x", padx=12, pady=(0, 6))

        self.nav_buttons = {}
        entries = [
            ("Inicio", "⌂", "MENÚ PRINCIPAL"),
            ("Datos en vivo", "◉", "DATOS EN VIVO"),
            ("Sensores por sistema", "▤", "SENSORES POR SISTEMA"),
            ("Osciloscopio ECU", "≋", "OSCILOSCOPIO ECU"),
            ("Escaneo y códigos", "⚠", "ESCANEO Y CÓDIGOS"),
            ("Escaneo profundo", "◎", "ESCANEO PROFUNDO"),
            ("Pruebas funcionales", "✓", "PRUEBAS GUIADAS"),
            ("Información del vehículo", "▣", "INFORMACIÓN ECU"),
            ("Informe Premium", "PDF", "INFORME PREMIUM"),
            ("Historial", "◷", "HISTORIAL"),
            ("Conexión", "⚙", "AJUSTES / CONEXIÓN"),
            ("Ayuda", "?", "AYUDA"),
        ]
        for page, icon, label in entries:
            button = tk.Button(
                self.sidebar,
                text=f"{icon:>3}   {label}",
                anchor="w",
                relief="flat",
                bd=0,
                bg="#060A0F",
                fg="#D5DCE4",
                activebackground="#1A2530",
                activeforeground=ORANGE_LIGHT,
                font=("Segoe UI", 10, "bold"),
                padx=13,
                pady=8,
                cursor="hand2",
                command=lambda target=page: self._show_page(target),
            )
            button.pack(fill="x", padx=7, pady=1)
            self.nav_buttons[page] = button

        footer = tk.Frame(self.sidebar, bg="#060A0F")
        footer.pack(side="bottom", fill="x", padx=12, pady=10)
        self.side_connection = tk.Label(
            footer,
            text="● SIN CONEXIÓN",
            bg="#060A0F",
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
            wraplength=215,
        )
        self.side_connection.pack(anchor="w")
        tk.Label(
            footer,
            text=f"Autor: {APP_AUTHOR}",
            bg="#060A0F",
            fg="#6F7E8C",
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(7, 0))

    def _build_header(self, parent) -> None:
        header = tk.Frame(parent, bg="#03070B", height=82, highlightbackground="#2B3946", highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg="#03070B")
        left.pack(side="left", fill="y", padx=18)
        title_box = tk.Frame(left, bg="#03070B")
        title_box.pack(side="left", pady=12)
        tk.Label(
            title_box,
            text="AUTOGUARD SCAN DIOS v6.2",
            bg="#03070B",
            fg=ORANGE,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        self.current_section_var = tk.StringVar(value="Menú principal")
        tk.Label(
            title_box,
            textvariable=self.current_section_var,
            bg="#03070B",
            fg="#D0D7DF",
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(3, 0))

        controls = tk.Frame(header, bg="#03070B")
        controls.pack(side="right", fill="y", padx=12)
        self.scanner_mode_button = tk.Button(
            controls,
            text="MODO ESCÁNER",
            bg=ORANGE,
            fg="white",
            activebackground=ORANGE_DARK,
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=13,
            pady=7,
            cursor="hand2",
            command=self._toggle_scanner_mode,
        )
        self.scanner_mode_button.pack(side="left", padx=5, pady=21)
        self.fullscreen_button = tk.Button(
            controls,
            text="PANTALLA COMPLETA",
            bg="#1A2632",
            fg=TEXT,
            activebackground="#314151",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=7,
            cursor="hand2",
            command=self._toggle_fullscreen,
        )
        self.fullscreen_button.pack(side="left", padx=5, pady=21)
        self.window_button = tk.Button(
            controls,
            text="VENTANA NORMAL",
            bg="#1A2632",
            fg=TEXT,
            activebackground="#314151",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=7,
            cursor="hand2",
            command=self._restore_normal_window,
        )
        self.window_button.pack(side="left", padx=5, pady=21)

        status = tk.Frame(header, bg="#03070B")
        status.pack(side="right", fill="y", padx=12)
        self.header_protocol = tk.Label(status, text="Protocolo: sin conexión", bg="#03070B", fg=MUTED, font=("Segoe UI", 9))
        self.header_protocol.pack(anchor="e", pady=(17, 2))
        self.header_status = tk.Label(status, text="● DESCONECTADO", bg="#03070B", fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.header_status.pack(anchor="e")

    def _toggle_fullscreen(self) -> None:
        self.fullscreen_enabled = not self.fullscreen_enabled
        self.attributes("-fullscreen", self.fullscreen_enabled)
        self.fullscreen_button.configure(text="SALIR PANTALLA COMPLETA" if self.fullscreen_enabled else "PANTALLA COMPLETA")

    def _exit_fullscreen(self) -> None:
        if self.fullscreen_enabled:
            self.fullscreen_enabled = False
            self.attributes("-fullscreen", False)
            self.fullscreen_button.configure(text="PANTALLA COMPLETA")

    def _restore_normal_window(self) -> None:
        self._exit_fullscreen()
        try:
            self.state("normal")
        except Exception:
            pass
        self.geometry("1500x880")
        self.update_idletasks()

    def _toggle_scanner_mode(self) -> None:
        self.scanner_mode_enabled = not self.scanner_mode_enabled
        if self.scanner_mode_enabled:
            self.scanner_mode_button.configure(text="SALIR MODO ESCÁNER", bg="#A84600")
            self._show_page("Escaneo y códigos")
            if not self.fullscreen_enabled:
                self._toggle_fullscreen()
            self._set_status("Modo escáner activo · Escaneo y códigos")
            if self.client.connected:
                self.after(250, self._scan_dtcs)
        else:
            self.scanner_mode_button.configure(text="MODO ESCÁNER", bg=ORANGE)
            self._exit_fullscreen()
            self._show_page("Inicio")
            self._set_status("Modo escáner finalizado")

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    def _build_pages(self) -> None:
        super()._build_pages()
        self._build_sensor_page(self._new_page("Sensores por sistema"))
        # FinalDiosApp expects a multi-scope widget. Reuse the dedicated page.
        self.multi_scope = self.scope_page_canvas

    def _show_page(self, name: str) -> None:
        if not hasattr(self, "pages") or name not in self.pages:
            return
        super()._show_page(name)
        labels = {
            "Inicio": "Menú principal y accesos directos",
            "Datos en vivo": "Panel de lecturas principales, relojes y estado de la sesión",
            "Sensores por sistema": "Selección, lectura y ventanas individuales por sensor",
            "Osciloscopio ECU": "Osciloscopio multicanal de telemetría ECU",
            "Escaneo y códigos": "Códigos activos, soluciones offline e historial de borrado",
            "Escaneo profundo": "Escaneo profundo OBD-II y UDS de solo lectura",
            "Pruebas funcionales": "Pruebas guiadas para confirmar el diagnóstico",
            "Información del vehículo": "Identificación del vehículo, módulos y ECU",
            "Informe Premium": "Informe PDF Premium con gráficos y plan de acción",
            "Historial": "Historial de sesiones, capturas y operaciones",
            "Conexión": "Conexión ELM327, puertos COM, WiFi y simulador",
            "Ayuda": "Ayuda técnica y alcance de la aplicación",
        }
        if self.current_section_var is not None:
            self.current_section_var.set(labels.get(name, name))

    def _build_home(self, page: tk.Frame) -> None:
        page.configure(bg=BG)
        title = tk.Frame(page, bg=BG)
        title.pack(fill="x", pady=(4, 16))
        tk.Label(title, text="MENÚ PRINCIPAL", bg=BG, fg=TEXT, font=("Segoe UI", 25, "bold")).pack(anchor="w")
        tk.Label(title, text="Seleccione una función para iniciar el diagnóstico", bg=BG, fg=MUTED, font=("Segoe UI", 12)).pack(anchor="w", pady=(3, 0))

        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="both", expand=True)
        for column in range(3):
            cards.columnconfigure(column, weight=1)
        for row in range(3):
            cards.rowconfigure(row, weight=1)

        options = [
            ("DATOS EN VIVO", "Lecturas principales, relojes, combustible y estado ECU", "Datos en vivo", "◉"),
            ("SENSORES POR SISTEMA", "Motor, combustible, admisión, emisiones y ventanas individuales", "Sensores por sistema", "▤"),
            ("OSCILOSCOPIO ECU", "Hasta ocho canales de telemetría en tiempo real", "Osciloscopio ECU", "≋"),
            ("ESCANEO Y CÓDIGOS", "DTC encontrados, descripción, solución y códigos borrados", "Escaneo y códigos", "⚠"),
            ("ESCANEO PROFUNDO", "Módulos, VIN, Mode 06/09, freeze frame y datos UDS", "Escaneo profundo", "◎"),
            ("INFORME PREMIUM", "PDF profesional con gráficos y plan de acción", "Informe Premium", "PDF"),
            ("PRUEBAS GUIADAS", "Procesos técnicos para confirmar causas y reparaciones", "Pruebas funcionales", "✓"),
            ("INFORMACIÓN ECU", "Vehículo, protocolo, calibraciones y módulos detectados", "Información del vehículo", "▣"),
            ("AJUSTES / CONEXIÓN", "ELM327 mediante COM, WiFi o simulador", "Conexión", "⚙"),
        ]
        for index, (heading, description, target, icon) in enumerate(options):
            row, column = divmod(index, 3)
            card = tk.Frame(cards, bg=PANEL, highlightbackground="#334353", highlightthickness=1, cursor="hand2")
            card.grid(row=row, column=column, sticky="nsew", padx=7, pady=7)
            icon_label = tk.Label(card, text=icon, bg=PANEL, fg=ORANGE, font=("Segoe UI", 28, "bold"), cursor="hand2")
            icon_label.pack(anchor="w", padx=18, pady=(15, 3))
            heading_label = tk.Label(card, text=heading, bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold"), cursor="hand2")
            heading_label.pack(anchor="w", padx=18)
            description_label = tk.Label(card, text=description, bg=PANEL, fg=MUTED, font=("Segoe UI", 10), wraplength=360, justify="left", cursor="hand2")
            description_label.pack(anchor="w", padx=18, pady=(7, 14))
            for widget in (card, icon_label, heading_label, description_label):
                widget.bind("<Button-1>", lambda _event, page_name=target: self._show_page(page_name))

        # Compatibility/status widgets used by the diagnostic engine.
        self.card_connection = self._card(page, "Conexión", "Desconectado")
        self.card_protocol = self._card(page, "Protocolo", "Sin detectar")
        self.card_dtc = self._card(page, "DTC", "0")
        self.card_database = self._card(page, "Base", str(self.db_stats.get("unique_codes", 0)))
        for widget in (self.card_connection, self.card_protocol, self.card_dtc, self.card_database):
            widget.pack_forget()
        self.home_live = ttk.Treeview(page, columns=("parameter", "value", "unit", "pid"), show="headings")
        self.home_items = {}
        for pid in (0x0C, 0x0D, 0x05, 0x42, 0x2F, 0x5E):
            name, unit = PID_DEFINITIONS[pid]
            self.home_items[pid] = self.home_live.insert("", "end", values=(name, "--", unit, f"01{pid:02X}"))
        self.home_console = tk.Text(page)

    def _build_live(self, page: tk.Frame) -> None:
        page.configure(bg=BG)
        self._section_title(page, "Datos en vivo", "Lecturas principales de la ECU sin mezclar el selector de sensores ni el osciloscopio")

        self.pid_vars = {pid: tk.BooleanVar(value=pid in DEFAULT_LIVE_PIDS) for pid in PID_DEFINITIONS}

        status_panel = self._panel(page, height=92)
        status_panel.pack(fill="x", pady=(0, 9))
        status_panel.pack_propagate(False)
        for column in range(4):
            status_panel.columnconfigure(column, weight=1)
        self.live_connection_var = tk.StringVar(value="Desconectado")
        self.live_protocol_var = tk.StringVar(value="Sin detectar")
        self.live_vehicle_var = tk.StringVar(value="Vehículo no identificado")
        self.live_session_var = tk.StringVar(value="00:00:00")
        blocks = [
            ("CONEXIÓN ELM327", self.live_connection_var, "Puerto / adaptador"),
            ("PROTOCOLO", self.live_protocol_var, "Detección automática"),
            ("VEHÍCULO", self.live_vehicle_var, "VIN / ECU"),
            ("TIEMPO DE SESIÓN", self.live_session_var, "Registro activo"),
        ]
        for index, (heading, variable, subtitle) in enumerate(blocks):
            frame = tk.Frame(status_panel, bg=PANEL)
            frame.grid(row=0, column=index, sticky="nsew", padx=15, pady=11)
            tk.Label(frame, text=heading, bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(frame, textvariable=variable, bg=PANEL, fg=GREEN if index == 0 else TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(3, 1))
            tk.Label(frame, text=subtitle, bg=PANEL, fg="#748393", font=("Segoe UI", 8)).pack(anchor="w")

        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        gauge_panel = self._panel(body)
        gauge_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        gauge_panel.columnconfigure(0, weight=1)
        gauge_panel.columnconfigure(1, weight=1)
        gauge_panel.rowconfigure(0, weight=1)
        gauge_panel.rowconfigure(1, weight=1)
        self.live_gauge_rpm = RealisticGauge(gauge_panel, "RPM MOTOR", "rpm", 0, 7000, 4800, 6200, size=240)
        self.live_gauge_speed = RealisticGauge(gauge_panel, "VELOCIDAD", "km/h", 0, 240, 160, 210, size=240)
        self.live_gauge_voltage = RealisticGauge(gauge_panel, "VOLTAJE", "V", 8, 18, 15.2, 16.4, size=240)
        self.live_gauge_coolant = RealisticGauge(gauge_panel, "REFRIGERANTE", "°C", 40, 130, 100, 115, size=240)
        self.live_gauge_map = RealisticGauge(gauge_panel, "PRESIÓN MAP", "kPa", 0, 255, 110, 180, size=240)
        self.live_gauge_oil = RealisticGauge(gauge_panel, "TEMP. ACEITE", "°C", 40, 200, 115, 145, size=240)
        visible_gauges = (self.live_gauge_rpm, self.live_gauge_speed, self.live_gauge_voltage, self.live_gauge_coolant)
        for index, gauge in enumerate(visible_gauges):
            gauge.grid(row=index // 2, column=index % 2, sticky="nsew", padx=7, pady=7)
        # Compatibility aliases used by the original engine.
        self.gauge_rpm = self.live_gauge_rpm
        self.gauge_speed = self.live_gauge_speed
        self.gauge_temp = self.live_gauge_coolant
        self.gauge_voltage = self.live_gauge_voltage

        summary = self._panel(body)
        summary.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(summary, text="LECTURAS PRINCIPALES", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(11, 7))
        self.dashboard_tree = ttk.Treeview(summary, columns=("sensor", "value", "unit", "pid"), show="headings", style="Final.Treeview", height=9)
        for column, title, width in (("sensor", "Sensor", 235), ("value", "Valor", 80), ("unit", "Unidad", 70), ("pid", "PID", 70)):
            self.dashboard_tree.heading(column, text=title)
            self.dashboard_tree.column(column, width=width, anchor="w")
        self.dashboard_tree.pack(fill="x", padx=10)
        for pid in (0x0C, 0x0D, 0x05, 0x0B, 0x42, 0x10, 0x2F, 0x5E):
            name, unit = PID_DEFINITIONS[pid]
            self.dashboard_items[pid] = self.dashboard_tree.insert("", "end", values=(name, "--", unit, f"01{pid:02X}"))

        flow = tk.Frame(summary, bg="#080E14", highlightbackground="#304050", highlightthickness=1)
        flow.pack(fill="x", padx=10, pady=10)
        flow.columnconfigure(0, weight=1)
        flow.columnconfigure(1, weight=1)
        self.direct_flow_value = tk.StringVar(value="N/D")
        self.estimated_flow_value = tk.StringVar(value="N/D")
        self.flow_difference_var = tk.StringVar(value="Esperando datos")
        for index, (heading, variable) in enumerate((("FLUJO DIRECTO PID 015E", self.direct_flow_value), ("ESTIMADO DESDE MAF", self.estimated_flow_value))):
            card = tk.Frame(flow, bg="#080E14")
            card.grid(row=0, column=index, sticky="nsew", padx=9, pady=8)
            tk.Label(card, text=heading, bg="#080E14", fg=MUTED, font=("Segoe UI", 8, "bold")).pack()
            tk.Label(card, textvariable=variable, bg="#080E14", fg=ORANGE, font=("Segoe UI", 24, "bold")).pack(pady=2)
            tk.Label(card, text="L/h", bg="#080E14", fg=TEXT, font=("Segoe UI", 9)).pack()
        self.fuel_source_label = tk.Label(summary, text="Flujómetro: no disponible", bg=PANEL, fg=ORANGE_LIGHT, font=("Segoe UI", 9, "bold"))
        self.fuel_source_label.pack(anchor="w", padx=12)
        tk.Label(summary, textvariable=self.flow_difference_var, bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(2, 8))

        self.live_mil_var = tk.StringVar(value="MIL: no informado")
        self.live_monitor_var = tk.StringVar(value="Monitores OBD-II: no leídos")
        self.live_mode_var = tk.StringVar(value="Modo de prueba: lectura estándar")
        for variable in (self.live_mil_var, self.live_monitor_var, self.live_mode_var):
            tk.Label(summary, textvariable=variable, bg=PANEL, fg="#C8D0D8", font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=12, pady=2)

        actions = self._panel(page, height=72)
        actions.pack(fill="x", pady=(9, 0))
        actions.pack_propagate(False)
        ttk.Button(actions, text="INICIAR LECTURA", style="Accent.TButton", command=self._start_live).pack(side="left", padx=(12, 6), pady=14)
        ttk.Button(actions, text="DETENER", command=self._stop_live).pack(side="left", padx=6, pady=14)
        ttk.Button(actions, text="SENSORES POR SISTEMA", command=lambda: self._show_page("Sensores por sistema")).pack(side="left", padx=6, pady=14)
        ttk.Button(actions, text="OSCILOSCOPIO ECU", command=lambda: self._show_page("Osciloscopio ECU")).pack(side="left", padx=6, pady=14)
        ttk.Button(actions, text="CAPTURAR DATOS", command=self._capture_sample).pack(side="right", padx=(6, 12), pady=14)
        ttk.Button(actions, text="EXPORTAR CSV", command=self._export_live_csv).pack(side="right", padx=6, pady=14)

        # DTC preview used by the diagnostic engine.
        self.live_dtc_tree = ttk.Treeview(page, columns=("code", "description"), show="headings")

    def _build_sensor_page(self, page: tk.Frame) -> None:
        page.configure(bg=BG)
        self._section_title(page, "Sensores por sistema", "Seleccione sensores, inicie la lectura y abra una ventana individual con doble clic")
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=430)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = self._panel(body, width=430)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        left.grid_propagate(False)
        tk.Label(left, text="SISTEMAS Y SENSORES", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(11, 7))
        self.sensor_search_var = tk.StringVar()
        search = ttk.Entry(left, textvariable=self.sensor_search_var)
        search.pack(fill="x", padx=10, pady=(0, 8))
        search.bind("<KeyRelease>", lambda _event: self._filter_sensor_tree())
        self.sensor_tree = ttk.Treeview(left, columns=("check", "pid", "unit"), show="tree headings", style="Final.Treeview")
        self.sensor_tree.heading("#0", text="Sensor / sistema")
        self.sensor_tree.heading("check", text="Sel.")
        self.sensor_tree.heading("pid", text="PID")
        self.sensor_tree.heading("unit", text="Unidad")
        self.sensor_tree.column("#0", width=245, anchor="w")
        self.sensor_tree.column("check", width=45, anchor="center")
        self.sensor_tree.column("pid", width=65, anchor="center")
        self.sensor_tree.column("unit", width=65, anchor="center")
        sensor_scroll = ttk.Scrollbar(left, orient="vertical", command=self.sensor_tree.yview)
        self.sensor_tree.configure(yscrollcommand=sensor_scroll.set)
        self.sensor_tree.pack(side="left", fill="both", expand=True, padx=(9, 0), pady=(0, 102))
        sensor_scroll.pack(side="right", fill="y", padx=(0, 8), pady=(0, 102))
        self.sensor_tree.bind("<Button-1>", self._sensor_tree_click)
        self.sensor_tree.bind("<Double-1>", self._sensor_tree_double_click)
        self.sensor_tree_items = {}
        self._populate_sensor_tree()
        self.selected_sensor_label = tk.Label(left, text="Seleccionados", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.selected_sensor_label.place(relx=0.035, rely=0.865)
        controls = tk.Frame(left, bg=PANEL)
        controls.place(relx=0.025, rely=0.90, relwidth=0.95, height=74)
        ttk.Button(controls, text="Soportados", command=self._select_supported).pack(side="left", fill="x", expand=True, padx=3, pady=5)
        ttk.Button(controls, text="Todos", command=lambda: self._set_sensor_selection(True)).pack(side="left", fill="x", expand=True, padx=3, pady=5)
        ttk.Button(controls, text="Limpiar", command=lambda: self._set_sensor_selection(False)).pack(side="left", fill="x", expand=True, padx=3, pady=5)

        right = self._panel(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        toolbar = tk.Frame(right, bg=PANEL)
        toolbar.pack(fill="x", padx=10, pady=9)
        tk.Label(toolbar, text="LECTURA DETALLADA", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(toolbar, text="Iniciar lectura", style="Accent.TButton", command=self._start_live).pack(side="right", padx=4)
        ttk.Button(toolbar, text="Detener", command=self._stop_live).pack(side="right", padx=4)
        ttk.Button(toolbar, text="Abrir sensor", command=self._open_selected_sensor_window).pack(side="right", padx=4)

        columns = ("parameter", "value", "unit", "minimum", "maximum", "pid")
        self.live_tree = ttk.Treeview(right, columns=columns, show="headings", style="Final.Treeview")
        for column, title, width in (
            ("parameter", "Sensor", 330), ("value", "Actual", 100), ("unit", "Unidad", 80),
            ("minimum", "Mínimo", 100), ("maximum", "Máximo", 100), ("pid", "PID", 80),
        ):
            self.live_tree.heading(column, text=title)
            self.live_tree.column(column, width=width, anchor="w")
        live_scroll = ttk.Scrollbar(right, orient="vertical", command=self.live_tree.yview)
        self.live_tree.configure(yscrollcommand=live_scroll.set)
        self.live_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        live_scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))
        self.live_tree.bind("<Double-1>", self._trace_double_click)
        self.live_items = {}
        for pid, (name, unit) in PID_DEFINITIONS.items():
            self.live_items[pid] = self.live_tree.insert("", "end", values=(name, "--", unit, "--", "--", f"01{pid:02X}"))

        note = tk.Label(
            right,
            text="Doble clic sobre un sensor para abrir su ventana individual con valor, mínimo, promedio, máximo, gráfico y exportación CSV.",
            bg=PANEL,
            fg=ORANGE_LIGHT,
            font=("Segoe UI", 9, "bold"),
            wraplength=850,
            justify="left",
        )
        note.place(relx=0.02, rely=0.955)

    def _open_selected_sensor_window(self) -> None:
        selection = self.live_tree.selection()
        if not selection:
            messagebox.showinfo("Sensor", "Seleccione un sensor de la tabla o utilice doble clic.")
            return
        values = self.live_tree.item(selection[0], "values")
        if len(values) < 6 or not str(values[5]).startswith("01"):
            return
        pid = int(str(values[5])[2:], 16)
        window = self.sensor_windows.get(pid)
        if window is not None and window.winfo_exists():
            window.lift()
            window.focus_force()
            return
        self.sensor_windows[pid] = SensorDetailWindow(self, pid)

    def _build_report(self, page: tk.Frame) -> None:
        page.configure(bg=BG)
        self._section_title(page, "Informe PDF Premium", "Formulario ordenado por secciones, gráficos, DTC y plan de acción")
        notebook = ttk.Notebook(page)
        notebook.pack(fill="both", expand=True)

        vehicle_tab = tk.Frame(notebook, bg=PANEL)
        notes_tab = tk.Frame(notebook, bg=PANEL)
        output_tab = tk.Frame(notebook, bg=PANEL)
        notebook.add(vehicle_tab, text="1. DATOS DEL VEHÍCULO")
        notebook.add(notes_tab, text="2. DIAGNÓSTICO Y OBSERVACIONES")
        notebook.add(output_tab, text="3. GENERAR INFORME")

        fields = [
            ("cliente", "Cliente"), ("patente", "Patente"), ("marca", "Marca"),
            ("modelo", "Modelo"), ("anio", "Año"), ("vin", "VIN"),
            ("kilometraje", "Kilometraje"), ("motor", "Motor"), ("tecnico", "Técnico"),
        ]
        self.report_vars = {}
        form = tk.Frame(vehicle_tab, bg=PANEL)
        form.pack(fill="both", expand=True, padx=28, pady=24)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        for index, (key, label) in enumerate(fields):
            row = index // 2
            group = index % 2
            variable = tk.StringVar(value=APP_AUTHOR if key == "tecnico" else "")
            self.report_vars[key] = variable
            label_column = group * 2
            entry_column = label_column + 1
            tk.Label(form, text=label, bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).grid(row=row, column=label_column, sticky="w", padx=(0 if group == 0 else 28, 12), pady=13)
            ttk.Entry(form, textvariable=variable, font=("Segoe UI", 11)).grid(row=row, column=entry_column, sticky="ew", padx=(0, 12), pady=13, ipady=5)
        tk.Label(
            form,
            text="Los datos de VIN, ECU y protocolo detectados durante el escaneo profundo también se incorporarán al informe cuando estén disponibles.",
            bg=PANEL,
            fg=ORANGE_LIGHT,
            font=("Segoe UI", 10, "bold"),
            wraplength=1050,
            justify="left",
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(28, 0))

        tk.Label(notes_tab, text="OBSERVACIONES, SÍNTOMAS, MEDICIONES Y RECOMENDACIONES", bg=PANEL, fg=ORANGE, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=22, pady=(20, 8))
        self.report_notes = tk.Text(notes_tab, bg="#060B10", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 11))
        notes_scroll = ttk.Scrollbar(notes_tab, orient="vertical", command=self.report_notes.yview)
        self.report_notes.configure(yscrollcommand=notes_scroll.set)
        self.report_notes.pack(side="left", fill="both", expand=True, padx=(22, 0), pady=(0, 22))
        notes_scroll.pack(side="right", fill="y", padx=(0, 22), pady=(0, 22))
        self.report_notes.insert("end", "Registrar síntomas, condiciones de la prueba, mediciones confirmatorias, reparación realizada y recomendaciones del técnico.")

        output = tk.Frame(output_tab, bg=PANEL)
        output.pack(fill="both", expand=True, padx=28, pady=24)
        tk.Label(output, text="CONTENIDO DEL INFORME PREMIUM", bg=PANEL, fg=ORANGE, font=("Segoe UI", 15, "bold")).pack(anchor="w")
        content = (
            "✓ Datos del cliente, vehículo, VIN, ECU y protocolo\n\n"
            "✓ Códigos encontrados con estado, severidad y descripción\n\n"
            "✓ Causas probables y posible solución paso a paso\n\n"
            "✓ Sensores, herramientas y validación posterior\n\n"
            "✓ Datos en vivo, valores mínimos y máximos\n\n"
            "✓ Gráficos vectoriales de la sesión\n\n"
            "✓ Observaciones, conclusión técnica y firmas"
        )
        tk.Label(output, text=content, bg=PANEL, fg=TEXT, font=("Segoe UI", 12), justify="left").pack(anchor="w", pady=(18, 24))
        ttk.Button(output, text="GENERAR INFORME PDF PREMIUM", style="Accent.TButton", command=self._generate_report).pack(anchor="w", ipady=5)
        self.report_status = tk.Label(output, text="El informe se guardará en la ubicación seleccionada.", bg=PANEL, fg=MUTED, font=("Segoe UI", 10), wraplength=1000, justify="left")
        self.report_status.pack(anchor="w", pady=(14, 0))

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------
    def _drain_queues(self) -> None:
        super()._drain_queues()
        if hasattr(self, "dashboard_tree"):
            for pid, item in self.dashboard_items.items():
                name, unit = PID_DEFINITIONS[pid]
                value = self.latest_values.get(pid)
                self.dashboard_tree.item(item, values=(name, format_value(value) if value is not None else "--", unit, f"01{pid:02X}"))
        if hasattr(self, "live_gauge_rpm"):
            self.live_gauge_rpm.set_value(self.latest_values.get(0x0C, 0), 0x0C in self.latest_values)
            self.live_gauge_speed.set_value(self.latest_values.get(0x0D, 0), 0x0D in self.latest_values)
        if hasattr(self, "direct_flow_value"):
            direct = self.latest_values.get(0x5E)
            maf = self.latest_values.get(0x10)
            estimated = premium_module.estimate_fuel_rate_from_maf(maf) if maf is not None else None
            self.direct_flow_value.set(format_value(direct) if direct is not None and "directa" in self.fuel_source.casefold() else "N/D")
            self.estimated_flow_value.set(format_value(estimated) if estimated is not None else "N/D")
            if direct is not None and estimated not in (None, 0):
                self.flow_difference_var.set(f"Diferencia: {abs(direct - estimated) / estimated * 100:.1f} %")
            else:
                self.flow_difference_var.set(self.fuel_source)


def main() -> None:
    app = NavigationPremiumApp()
    app.mainloop()


if __name__ == "__main__":
    main()
