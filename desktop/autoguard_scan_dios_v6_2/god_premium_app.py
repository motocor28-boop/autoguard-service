from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

import final_dios_app as final_module
from core import PID_DEFINITIONS
from dtc_database import DTCRecord, DTCSolution, resource_path
from final_dios_app import DEFAULT_LIVE_PIDS, FINAL_BUILD, SENSOR_SYSTEMS, FinalDiosApp
from final_widgets import MultiTraceCanvas, TRACE_COLORS, format_value
from premium_app import (
    APP_AUTHOR,
    BG,
    GREEN,
    MUTED,
    ORANGE,
    ORANGE_DARK,
    ORANGE_LIGHT,
    PANEL,
    RED,
    SIDEBAR,
    TEXT,
    YELLOW,
)
from premium_gauges import RealisticGauge

# FinalDiosApp resolves Gauge through its module global when _build_live runs.
final_module.Gauge = RealisticGauge

GOD_VERSION = "6.2.1 NIVEL DIOS PREMIUM"
GOD_BUILD = "Edición limpia · Escaneo profundo · Diagnóstico offline · Full HD"


@dataclass(slots=True)
class ScanDisplayRecord:
    record: DTCRecord
    status: str
    solution: DTCSolution | None


class GodPremiumApp(FinalDiosApp):
    """Clean final edition using the user-approved dark/orange workshop layout."""

    def __init__(self) -> None:
        self.clean_events: "queue.Queue[tuple]" = queue.Queue()
        self.deleted_codes: list[dict[str, str]] = []
        self.active_scan_records: list[ScanDisplayRecord] = []
        self.scan_item_data: dict[str, ScanDisplayRecord] = {}
        self.scope_page_pids: list[int] = list(DEFAULT_LIVE_PIDS)
        self.scope_tree_items: dict[int, str] = {}
        self.scope_trace_items: dict[int, str] = {}
        super().__init__()
        self.title(f"AUTOGUARD SCAN DIOS v{GOD_VERSION}")
        self._show_page("Datos en vivo")

    # ------------------------------------------------------------------
    # Branding and clean navigation
    # ------------------------------------------------------------------
    def _load_brand(self, size: tuple[int, int]) -> ImageTk.PhotoImage | None:
        try:
            image = Image.open(resource_path("autoguard.png")).convert("RGBA")
            image.thumbnail(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def _build_sidebar(self) -> None:
        self.sidebar.configure(
            bg="#070B10",
            width=146,
            highlightbackground="#2A3744",
            highlightthickness=1,
        )
        self.sidebar.pack_propagate(False)
        for child in self.sidebar.winfo_children():
            child.destroy()

        brand = tk.Frame(self.sidebar, bg="#070B10")
        brand.pack(fill="x", pady=(8, 12))
        self.sidebar_brand = self._load_brand((132, 76))
        if self.sidebar_brand is not None:
            tk.Label(brand, image=self.sidebar_brand, bg="#070B10").pack(padx=5)
        else:
            tk.Label(brand, text="AUTO GUARD", bg="#070B10", fg=ORANGE, font=("Segoe UI", 12, "bold")).pack(pady=10)
        tk.Label(brand, text="SCAN DIOS v6.2", bg="#070B10", fg="#D6DCE2", font=("Segoe UI", 8, "bold")).pack(pady=(2, 0))

        self.nav_buttons = {}
        menu = [
            ("Datos en vivo", "⌁", "Datos en vivo"),
            ("Osciloscopio ECU", "≋", "Osciloscopio"),
            ("Escaneo y códigos", "⚠", "Escaneo y códigos"),
            ("Escaneo profundo", "◎", "Escaneo profundo"),
            ("Pruebas funcionales", "▦", "Pruebas guiadas"),
            ("Información del vehículo", "▣", "Información ECU"),
            ("Informe Premium", "PDF", "Informe Premium"),
            ("Historial", "◷", "Historial"),
            ("Conexión", "⚙", "Ajustes"),
            ("Ayuda", "?", "Ayuda"),
        ]
        for page, icon, label in menu:
            button = tk.Button(
                self.sidebar,
                text=f"{icon}   {label}",
                anchor="w",
                relief="flat",
                bd=0,
                bg="#070B10",
                fg="#B4BEC9",
                activebackground="#1A2530",
                activeforeground=ORANGE_LIGHT,
                font=("Segoe UI", 8, "bold"),
                padx=10,
                pady=8,
                command=lambda target=page: self._show_page(target),
            )
            button.pack(fill="x", padx=5, pady=1)
            self.nav_buttons[page] = button

        footer = tk.Frame(self.sidebar, bg="#070B10")
        footer.pack(side="bottom", fill="x", padx=6, pady=8)
        self.side_connection = tk.Label(
            footer,
            text="● SIN CONEXIÓN",
            bg="#070B10",
            fg=MUTED,
            font=("Segoe UI", 7, "bold"),
            wraplength=130,
        )
        self.side_connection.pack()
        tk.Label(
            footer,
            text=f"Autor\n{APP_AUTHOR}",
            bg="#070B10",
            fg="#687683",
            font=("Segoe UI", 6),
            justify="center",
        ).pack(pady=(6, 0))

    def _build_header(self, parent) -> None:
        header = tk.Frame(parent, bg="#03070B", height=78, highlightbackground="#2B3946", highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg="#03070B")
        left.pack(side="left", fill="y", padx=12)
        self.header_brand = self._load_brand((130, 64))
        if self.header_brand is not None:
            tk.Label(left, image=self.header_brand, bg="#03070B").pack(side="left", padx=(0, 12), pady=5)
        title_box = tk.Frame(left, bg="#03070B")
        title_box.pack(side="left", pady=11)
        tk.Label(
            title_box,
            text="AUTOGUARD SCAN DIOS v6.2",
            bg="#03070B",
            fg=ORANGE,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w")
        self.current_section_var = tk.StringVar(value="Datos en vivo")
        tk.Label(
            title_box,
            textvariable=self.current_section_var,
            bg="#03070B",
            fg="#C4CDD6",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(header, bg="#03070B")
        right.pack(side="right", fill="y", padx=14)
        tk.Label(right, text=GOD_VERSION, bg="#03070B", fg=ORANGE_LIGHT, font=("Segoe UI", 8, "bold")).pack(anchor="e", pady=(11, 2))
        self.header_protocol = tk.Label(right, text="Protocolo: sin conexión", bg="#03070B", fg=MUTED, font=("Segoe UI", 8))
        self.header_protocol.pack(anchor="e")
        self.header_status = tk.Label(right, text="● DESCONECTADO", bg="#03070B", fg=MUTED, font=("Segoe UI", 8, "bold"))
        self.header_status.pack(anchor="e", pady=(2, 0))

    def _build_pages(self) -> None:
        super()._build_pages()
        self._build_scope_page(self._new_page("Osciloscopio ECU"))
        self._build_scan_page(self._new_page("Escaneo y códigos"))

    def _show_page(self, name: str) -> None:
        super()._show_page(name)
        labels = {
            "Datos en vivo": "Datos en vivo y sensores por sistema",
            "Osciloscopio ECU": "Osciloscopio de telemetría entregada por la ECU",
            "Escaneo y códigos": "Escaneo limpio, códigos activos, borrado y soluciones",
            "Escaneo profundo": "Escaneo profundo OBD-II y UDS de solo lectura",
            "Pruebas funcionales": "Pruebas guiadas y tablas técnicas",
            "Información del vehículo": "Identificación del vehículo, ECU y protocolo",
            "Informe Premium": "Informe profesional Premium con gráficos y plan de acción",
            "Historial": "Historial de capturas, escaneos y códigos borrados",
            "Conexión": "Conexión ELM327 y ajustes",
            "Ayuda": "Ayuda, alcance y uso responsable",
        }
        if self.current_section_var is not None:
            self.current_section_var.set(labels.get(name, name))

    # ------------------------------------------------------------------
    # Dedicated oscilloscope page
    # ------------------------------------------------------------------
    def _build_scope_page(self, page: tk.Frame) -> None:
        page.configure(bg=BG)
        self._section_title(
            page,
            "Osciloscopio ECU",
            "Monitoreo multicanal de la telemetría que los módulos publican mediante OBD-II",
        )

        toolbar = self._panel(page, height=56)
        toolbar.pack(fill="x", pady=(0, 8))
        toolbar.pack_propagate(False)
        ttk.Button(toolbar, text="Iniciar monitoreo", style="Accent.TButton", command=self._start_scope_page).pack(side="left", padx=(10, 6), pady=10)
        ttk.Button(toolbar, text="Detener", command=self._stop_live).pack(side="left", padx=4, pady=10)
        ttk.Button(toolbar, text="Pausar / continuar", command=self._toggle_scope_page_pause).pack(side="left", padx=4, pady=10)
        tk.Label(toolbar, text="Ventana:", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(18, 4))
        self.scope_page_seconds_var = tk.StringVar(value="10 s")
        combo = ttk.Combobox(toolbar, textvariable=self.scope_page_seconds_var, values=["5 s", "10 s", "20 s", "30 s", "60 s"], state="readonly", width=8)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_scope_window())
        self.scope_page_status = tk.Label(toolbar, text="Seleccione hasta 8 sensores", bg=PANEL, fg=ORANGE_LIGHT, font=("Segoe UI", 8, "bold"))
        self.scope_page_status.pack(side="right", padx=12)

        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=330)
        body.columnconfigure(1, weight=5)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        sensor_panel = self._panel(body, width=330)
        sensor_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        sensor_panel.grid_propagate(False)
        tk.Label(sensor_panel, text="CANALES / SENSORES", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=8)
        tk.Label(sensor_panel, text="Doble clic para activar o desactivar", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(0, 6))
        self.scope_sensor_tree = ttk.Treeview(sensor_panel, columns=("selected", "pid", "unit"), show="tree headings", style="Final.Treeview")
        self.scope_sensor_tree.heading("#0", text="Sistema / sensor")
        self.scope_sensor_tree.heading("selected", text="Canal")
        self.scope_sensor_tree.heading("pid", text="PID")
        self.scope_sensor_tree.heading("unit", text="Unidad")
        self.scope_sensor_tree.column("#0", width=185)
        self.scope_sensor_tree.column("selected", width=48, anchor="center")
        self.scope_sensor_tree.column("pid", width=55, anchor="center")
        self.scope_sensor_tree.column("unit", width=55, anchor="center")
        scroll = ttk.Scrollbar(sensor_panel, orient="vertical", command=self.scope_sensor_tree.yview)
        self.scope_sensor_tree.configure(yscrollcommand=scroll.set)
        self.scope_sensor_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 45))
        scroll.pack(side="right", fill="y", padx=(0, 8), pady=(0, 45))
        self.scope_sensor_tree.bind("<Double-1>", self._toggle_scope_sensor)
        self._populate_scope_sensor_tree()
        ttk.Button(sensor_panel, text="Aplicar canales", style="Accent.TButton", command=self._apply_scope_channels).place(relx=0.05, rely=0.93, relwidth=0.90, height=34)

        graph_panel = self._panel(body)
        graph_panel.grid(row=0, column=1, sticky="nsew", padx=6)
        self.scope_page_canvas = MultiTraceCanvas(graph_panel)
        self.scope_page_canvas.bind_owner(self)
        self.scope_page_canvas.set_pids(self.scope_page_pids)
        self.scope_page_canvas.pack(fill="both", expand=True, padx=9, pady=9)

        legend_panel = self._panel(body)
        legend_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        tk.Label(legend_panel, text="LECTURAS DE CANAL", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=8)
        self.scope_trace_tree = ttk.Treeview(legend_panel, columns=("sensor", "value", "unit", "min", "max"), show="headings", style="Final.Treeview")
        for column, title, width in (
            ("sensor", "Sensor", 145), ("value", "Valor", 64), ("unit", "Unidad", 52), ("min", "Mín", 55), ("max", "Máx", 55),
        ):
            self.scope_trace_tree.heading(column, text=title)
            self.scope_trace_tree.column(column, width=width, anchor="w")
        self.scope_trace_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._refresh_scope_trace_rows()

        note = self._panel(page, height=54)
        note.pack(fill="x", pady=(8, 0))
        note.pack_propagate(False)
        tk.Label(
            note,
            text=(
                "Este osciloscopio muestra valores calculados y transmitidos por la ECU. "
                "Las señales eléctricas directas CKP, CMP, bobinas, inyectores, PWM y CAN H/L requieren hardware de osciloscopio externo."
            ),
            bg=PANEL,
            fg=YELLOW,
            font=("Segoe UI", 8, "bold"),
            wraplength=1300,
            justify="left",
        ).pack(anchor="w", padx=12, pady=10)

    def _populate_scope_sensor_tree(self) -> None:
        for item in self.scope_sensor_tree.get_children():
            self.scope_sensor_tree.delete(item)
        self.scope_tree_items.clear()
        used: set[int] = set()
        for system, pids in SENSOR_SYSTEMS.items():
            parent = self.scope_sensor_tree.insert("", "end", text=system, values=("", "", ""), open=system in {"Motor", "Combustible"})
            for pid in pids:
                if pid not in PID_DEFINITIONS or pid in used:
                    continue
                used.add(pid)
                name, unit = PID_DEFINITIONS[pid]
                selected = pid in self.scope_page_pids
                item = self.scope_sensor_tree.insert(parent, "end", text=name, values=("●" if selected else "○", f"01{pid:02X}", unit))
                self.scope_tree_items[pid] = item
        remaining = [pid for pid in PID_DEFINITIONS if pid not in used]
        if remaining:
            parent = self.scope_sensor_tree.insert("", "end", text="Otros parámetros", values=("", "", ""), open=False)
            for pid in remaining:
                name, unit = PID_DEFINITIONS[pid]
                item = self.scope_sensor_tree.insert(parent, "end", text=name, values=("●" if pid in self.scope_page_pids else "○", f"01{pid:02X}", unit))
                self.scope_tree_items[pid] = item

    def _toggle_scope_sensor(self, _event=None) -> None:
        selection = self.scope_sensor_tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.scope_sensor_tree.item(item, "values")
        if len(values) < 2 or not str(values[1]).startswith("01"):
            return
        pid = int(str(values[1])[2:], 16)
        if pid in self.scope_page_pids:
            self.scope_page_pids.remove(pid)
        else:
            if len(self.scope_page_pids) >= 8:
                messagebox.showinfo("Osciloscopio", "El máximo visible es de 8 canales simultáneos.")
                return
            self.scope_page_pids.append(pid)
        self._populate_scope_sensor_tree()
        self._apply_scope_channels(start_worker=False)

    def _apply_scope_channels(self, start_worker: bool = True) -> None:
        self.scope_page_pids = list(dict.fromkeys(self.scope_page_pids))[:8]
        self.scope_page_canvas.set_pids(self.scope_page_pids)
        self._refresh_scope_trace_rows()
        self.scope_page_status.configure(text=f"{len(self.scope_page_pids)} canales seleccionados")
        if start_worker:
            self._start_scope_page()

    def _start_scope_page(self) -> None:
        if not self.client.connected:
            messagebox.showwarning("Osciloscopio", "Conecte primero el ELM327 o utilice el simulador.")
            self._show_page("Conexión")
            return
        if not self.scope_page_pids:
            messagebox.showinfo("Osciloscopio", "Seleccione al menos un sensor.")
            return
        try:
            for pid, variable in self.pid_vars.items():
                if pid in self.scope_page_pids:
                    variable.set(True)
            selected = list(dict.fromkeys(self._selected_pids() + self.scope_page_pids))
            self._restart_worker(selected)
            self.scope_page_status.configure(text="Monitoreo activo", fg=GREEN)
        except Exception as exc:
            messagebox.showerror("Osciloscopio", str(exc))

    def _toggle_scope_page_pause(self) -> None:
        paused = not self.scope_page_canvas.paused
        self.scope_page_canvas.set_paused(paused)
        self.scope_page_status.configure(text="Pausado" if paused else "Monitoreo activo", fg=YELLOW if paused else GREEN)

    def _apply_scope_window(self) -> None:
        try:
            seconds = float(self.scope_page_seconds_var.get().split()[0])
        except (ValueError, IndexError):
            seconds = 10.0
        self.scope_page_canvas.set_time_window(seconds)

    def _refresh_scope_trace_rows(self) -> None:
        for item in self.scope_trace_tree.get_children():
            self.scope_trace_tree.delete(item)
        self.scope_trace_items.clear()
        for pid in self.scope_page_pids:
            name, unit = PID_DEFINITIONS.get(pid, (f"PID 01{pid:02X}", ""))
            self.scope_trace_items[pid] = self.scope_trace_tree.insert("", "end", values=(name, "--", unit, "--", "--"))

    # ------------------------------------------------------------------
    # Clean scan and codes page
    # ------------------------------------------------------------------
    def _build_scan_page(self, page: tk.Frame) -> None:
        page.configure(bg=BG)
        self._section_title(
            page,
            "Escaneo y códigos",
            "Muestra únicamente los códigos encontrados, sus descripciones y el plan de acción offline",
        )

        toolbar = self._panel(page, height=62)
        toolbar.pack(fill="x", pady=(0, 8))
        toolbar.pack_propagate(False)
        ttk.Button(toolbar, text="Escanear ECU", style="Accent.TButton", command=self._scan_dtcs).pack(side="left", padx=(10, 6), pady=12)
        ttk.Button(toolbar, text="Borrar códigos encontrados", command=self._clear_dtcs).pack(side="left", padx=6, pady=12)
        ttk.Button(toolbar, text="Escaneo profundo", command=lambda: self._show_page("Escaneo profundo")).pack(side="left", padx=6, pady=12)
        self.scan_status_var = tk.StringVar(value="Listo para escanear")
        tk.Label(toolbar, textvariable=self.scan_status_var, bg=PANEL, fg=ORANGE_LIGHT, font=("Segoe UI", 9, "bold")).pack(side="right", padx=12)

        state_panel = self._panel(page, height=78)
        state_panel.pack(fill="x", pady=(0, 8))
        state_panel.pack_propagate(False)
        self.scan_state_icon = tk.Label(state_panel, text="✓", bg=PANEL, fg=GREEN, font=("Segoe UI", 28, "bold"))
        self.scan_state_icon.pack(side="left", padx=(16, 12), pady=8)
        state_text = tk.Frame(state_panel, bg=PANEL)
        state_text.pack(side="left", fill="y", pady=9)
        self.scan_state_title = tk.Label(state_text, text="Sin códigos activos", bg=PANEL, fg=GREEN, font=("Segoe UI", 15, "bold"))
        self.scan_state_title.pack(anchor="w")
        self.scan_state_detail = tk.Label(state_text, text="Ejecute un escaneo para confirmar el estado de la ECU.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.scan_state_detail.pack(anchor="w", pady=(3, 0))
        self.scan_count_label = tk.Label(state_panel, text="0 códigos", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold"))
        self.scan_count_label.pack(side="right", padx=18)

        main = tk.PanedWindow(page, orient="horizontal", bg=BG, sashwidth=6, sashrelief="flat")
        main.pack(fill="both", expand=True)
        active_panel = self._panel(main)
        solution_panel = self._panel(main)
        main.add(active_panel, minsize=720)
        main.add(solution_panel, minsize=480)

        tk.Label(active_panel, text="CÓDIGOS ENCONTRADOS", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=8)
        self.scan_empty_label = tk.Label(
            active_panel,
            text="✓  SIN CÓDIGOS ACTIVOS",
            bg="#07110D",
            fg=GREEN,
            font=("Segoe UI", 17, "bold"),
            highlightbackground="#214C37",
            highlightthickness=1,
        )
        self.scan_empty_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.scan_tree_frame = tk.Frame(active_panel, bg=PANEL)
        columns = ("code", "status", "severity", "system", "description")
        self.scan_tree = ttk.Treeview(self.scan_tree_frame, columns=columns, show="headings", style="Final.Treeview")
        for column, title, width in (
            ("code", "Código", 90), ("status", "Estado", 105), ("severity", "Severidad", 100),
            ("system", "Sistema", 190), ("description", "Descripción", 440),
        ):
            self.scan_tree.heading(column, text=title)
            self.scan_tree.column(column, width=width, anchor="w")
        scan_scroll = ttk.Scrollbar(self.scan_tree_frame, orient="vertical", command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=scan_scroll.set)
        self.scan_tree.pack(side="left", fill="both", expand=True)
        scan_scroll.pack(side="right", fill="y")
        self.scan_tree.bind("<<TreeviewSelect>>", self._show_scan_solution)

        tk.Label(solution_panel, text="DESCRIPCIÓN Y POSIBLE SOLUCIÓN", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=8)
        self.scan_solution_text = tk.Text(solution_panel, bg="#050A0F", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 9))
        solution_scroll = ttk.Scrollbar(solution_panel, orient="vertical", command=self.scan_solution_text.yview)
        self.scan_solution_text.configure(yscrollcommand=solution_scroll.set)
        self.scan_solution_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        solution_scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))
        self.scan_solution_text.insert("end", "No existen códigos activos para analizar.")

        deleted_panel = self._panel(page, height=172)
        deleted_panel.pack(fill="x", pady=(8, 0))
        deleted_panel.pack_propagate(False)
        title_row = tk.Frame(deleted_panel, bg=PANEL)
        title_row.pack(fill="x")
        tk.Label(title_row, text="CÓDIGOS BORRADOS DURANTE LA SESIÓN", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=10, pady=7)
        self.deleted_count_label = tk.Label(title_row, text="0 registros", bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.deleted_count_label.pack(side="right", padx=10)
        self.deleted_tree = ttk.Treeview(deleted_panel, columns=("time", "code", "status", "description", "result"), show="headings", style="Final.Treeview", height=4)
        for column, title, width in (
            ("time", "Fecha / hora", 150), ("code", "Código", 90), ("status", "Estado previo", 110),
            ("description", "Descripción", 560), ("result", "Resultado", 190),
        ):
            self.deleted_tree.heading(column, text=title)
            self.deleted_tree.column(column, width=width, anchor="w")
        self.deleted_tree.pack(fill="both", expand=True, padx=9, pady=(0, 9))

    def _populate_dtc_tree(self, records: list[tuple[DTCRecord, str]]) -> None:
        super()._populate_dtc_tree(records)
        if not hasattr(self, "scan_tree"):
            return
        unique: dict[str, ScanDisplayRecord] = {}
        for record, status in records:
            if record.code in unique:
                continue
            solution = self.database.solution(record.code, record.manufacturer)
            unique[record.code] = ScanDisplayRecord(record=record, status=status, solution=solution)
        self.active_scan_records = list(unique.values())
        self._render_scan_records()

    def _render_scan_records(self) -> None:
        for item in self.scan_tree.get_children():
            self.scan_tree.delete(item)
        self.scan_item_data.clear()
        count = len(self.active_scan_records)
        self.scan_count_label.configure(text=f"{count} código{'s' if count != 1 else ''}")
        if not self.active_scan_records:
            self.scan_tree_frame.pack_forget()
            if not self.scan_empty_label.winfo_manager():
                self.scan_empty_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self.scan_state_icon.configure(text="✓", fg=GREEN)
            self.scan_state_title.configure(text="Sin códigos activos", fg=GREEN)
            self.scan_state_detail.configure(text="La ECU no informó códigos confirmados, pendientes ni permanentes.")
            self.scan_status_var.set("Escaneo finalizado · Sin códigos activos")
            self.scan_solution_text.delete("1.0", "end")
            self.scan_solution_text.insert("end", "SIN CÓDIGOS ACTIVOS\n\nNo existen códigos para mostrar. Mantenga este resultado como evidencia del escaneo.")
            return

        self.scan_empty_label.pack_forget()
        if not self.scan_tree_frame.winfo_manager():
            self.scan_tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.scan_state_icon.configure(text="!", fg=YELLOW)
        self.scan_state_title.configure(text="Códigos activos encontrados", fg=YELLOW)
        self.scan_state_detail.configure(text="Seleccione un código para revisar descripción, causas y posible solución.")
        self.scan_status_var.set(f"Escaneo finalizado · {len(self.active_scan_records)} códigos")
        for item in self.active_scan_records:
            solution = item.solution
            severity = solution.severity if solution else "Por confirmar"
            system = solution.system if solution else "Sistema no identificado"
            tree_item = self.scan_tree.insert(
                "",
                "end",
                values=(item.record.code, item.status, severity, system, item.record.description),
            )
            self.scan_item_data[tree_item] = item
        first = self.scan_tree.get_children()
        if first:
            self.scan_tree.selection_set(first[0])
            self.scan_tree.focus(first[0])
            self._show_scan_solution()

    def _show_scan_solution(self, _event=None) -> None:
        selection = self.scan_tree.selection()
        if not selection:
            return
        item = self.scan_item_data.get(selection[0])
        if item is None:
            return
        self.scan_solution_text.delete("1.0", "end")
        self.scan_solution_text.tag_configure("title", foreground=ORANGE, font=("Segoe UI", 14, "bold"))
        self.scan_solution_text.tag_configure("heading", foreground=ORANGE_LIGHT, font=("Segoe UI", 10, "bold"))
        self.scan_solution_text.insert("end", f"{item.record.code} · {item.record.description}\n", "title")
        self.scan_solution_text.insert("end", f"\nEstado: {item.status}\nFabricante: {item.record.manufacturer}\n")
        solution = item.solution
        if solution is None:
            self.scan_solution_text.insert("end", "\nNo existe una solución offline específica. Confirme el procedimiento con información OEM del vehículo.")
            return
        sections = (
            ("SISTEMA Y SEVERIDAD", f"{solution.system}\nSeveridad: {solution.severity}"),
            ("SÍNTOMAS PROBABLES", solution.symptoms),
            ("CAUSAS PROBABLES", solution.causes),
            ("POSIBLE SOLUCIÓN / PROCESO PASO A PASO", solution.steps),
            ("SENSORES RELACIONADOS", solution.sensors),
            ("HERRAMIENTAS", solution.tools),
            ("VALIDACIÓN FINAL", solution.validation),
        )
        for title, text in sections:
            self.scan_solution_text.insert("end", f"\n{title}\n", "heading")
            self.scan_solution_text.insert("end", f"{text}\n")

    def _clear_dtcs(self) -> None:
        if not self.client.connected:
            messagebox.showwarning("Borrar códigos", "No existe conexión activa.")
            return
        if not self.active_scan_records:
            messagebox.showinfo("Borrar códigos", "No hay códigos activos registrados en la pantalla de escaneo.")
            return
        if not messagebox.askyesno(
            "Borrar códigos",
            "¿Confirma el borrado? Guarde primero la evidencia y repare la causa antes de borrar.",
        ):
            return
        snapshot = list(self.active_scan_records)
        self.scan_status_var.set("Solicitando borrado a la ECU...")

        def task() -> None:
            try:
                confirmed = self.client.clear_dtcs()
                self.clean_events.put(("clear_result", confirmed, snapshot, ""))
            except Exception as exc:
                self.clean_events.put(("clear_result", False, snapshot, str(exc)))

        threading.Thread(target=task, daemon=True).start()

    def _handle_clear_result(self, confirmed: bool, snapshot: list[ScanDisplayRecord], error: str) -> None:
        if not confirmed:
            self.scan_status_var.set("La ECU no confirmó el borrado")
            messagebox.showerror("Borrar códigos", error or "La ECU no confirmó el borrado de los códigos.")
            return
        stamp = time.strftime("%d-%m-%Y %H:%M:%S")
        for item in snapshot:
            record = {
                "time": stamp,
                "code": item.record.code,
                "status": item.status,
                "description": item.record.description,
                "result": "Borrado confirmado por ECU",
            }
            self.deleted_codes.append(record)
            self.deleted_tree.insert(
                "",
                0,
                values=(record["time"], record["code"], record["status"], record["description"], record["result"]),
            )
        self.deleted_count_label.configure(text=f"{len(self.deleted_codes)} registros")
        self._record_history("Códigos borrados", ", ".join(item.record.code for item in snapshot))
        self.active_scan_records.clear()
        self._populate_dtc_tree([])
        self.scan_state_detail.configure(text="Borrado confirmado. Ejecute un nuevo escaneo para verificar que no reaparezcan.")
        self.scan_status_var.set("Borrado confirmado · Sin códigos activos en pantalla")
        messagebox.showinfo(
            "Borrado confirmado",
            f"La ECU confirmó el borrado de {len(snapshot)} código(s).\n\nLos códigos borrados quedaron registrados en la tabla inferior.",
        )

    # ------------------------------------------------------------------
    # Queue refresh and visual synchronization
    # ------------------------------------------------------------------
    def _drain_queues(self) -> None:
        super()._drain_queues()
        while True:
            try:
                event = self.clean_events.get_nowait()
            except queue.Empty:
                break
            if event[0] == "clear_result":
                self._handle_clear_result(bool(event[1]), event[2], str(event[3]))

        if hasattr(self, "scope_page_canvas"):
            self.scope_page_canvas.set_pids(self.scope_page_pids)
            self.scope_page_canvas.redraw()
            for pid, tree_item in self.scope_trace_items.items():
                name, unit = PID_DEFINITIONS.get(pid, (f"PID 01{pid:02X}", ""))
                value = self.latest_values.get(pid)
                minimum = self.min_values.get(pid)
                maximum = self.max_values.get(pid)
                self.scope_trace_tree.item(
                    tree_item,
                    values=(
                        name,
                        format_value(value) if value is not None else "--",
                        unit,
                        format_value(minimum) if minimum is not None else "--",
                        format_value(maximum) if maximum is not None else "--",
                    ),
                )


def main() -> None:
    app = GodPremiumApp()
    app.mainloop()


if __name__ == "__main__":
    main()
