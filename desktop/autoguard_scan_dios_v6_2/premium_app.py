from __future__ import annotations

import csv
import math
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
from collections import defaultdict, deque
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from PIL import Image, ImageTk

from core import ConnectionConfig, ELM327Client, LiveDataWorker, PID_DEFINITIONS, PID_RANGES
from dtc_database import DTCRecord, DtcDatabase, DTCSolution, resource_path
from reporting import default_report_path, generate_pdf_report

APP_NAME = "AUTOGUARD SCAN DIOS"
APP_VERSION = "6.2 PREMIUM"
APP_BUILD = "Edición naranja profesional 2026.07"
APP_AUTHOR = "Esteban Cortez Richards"

BG = "#090D12"
SIDEBAR = "#0C1118"
PANEL = "#121923"
PANEL_2 = "#182230"
PANEL_3 = "#202C3A"
TEXT = "#F5F7FA"
MUTED = "#98A4B3"
ORANGE = "#FF7A00"
ORANGE_LIGHT = "#FF9D3D"
ORANGE_DARK = "#B94E00"
GREEN = "#26C281"
YELLOW = "#F5C451"
RED = "#E5484D"
BLUE = "#4C9AFF"
GRID = "#263445"


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
        size: int = 230,
    ) -> None:
        super().__init__(master, width=size, height=size, bg=PANEL, highlightthickness=0)
        self.title = title
        self.unit = unit
        self.minimum = minimum
        self.maximum = maximum
        self.warning = warning
        self.danger = danger
        self.value = minimum
        self.signal = False
        self.bind("<Configure>", lambda _event: self.draw())
        self.draw()

    def set_value(self, value: float, signal: bool = True) -> None:
        self.value = max(self.minimum, min(self.maximum, float(value)))
        self.signal = signal
        self.draw()

    def _angle(self, value: float) -> float:
        ratio = (value - self.minimum) / max(self.maximum - self.minimum, 0.001)
        return math.radians(225.0 - ratio * 270.0)

    def draw(self) -> None:
        self.delete("all")
        width = max(180, self.winfo_width())
        height = max(180, self.winfo_height())
        size = min(width, height)
        cx, cy = width / 2, height / 2
        radius = size * 0.43

        for offset, color in (
            (0, "#8A949F"), (3, "#4B5561"), (7, "#252D37"),
            (11, "#0A0E13"), (16, "#141A22"),
        ):
            self.create_oval(
                cx - radius + offset, cy - radius + offset,
                cx + radius - offset, cy + radius - offset,
                fill=color, outline=color,
            )

        def zone(start_value: float, end_value: float, color: str) -> None:
            start = 225.0 - ((start_value - self.minimum) / (self.maximum - self.minimum)) * 270.0
            end = 225.0 - ((end_value - self.minimum) / (self.maximum - self.minimum)) * 270.0
            self.create_arc(
                cx - radius + 23, cy - radius + 23,
                cx + radius - 23, cy + radius - 23,
                start=end, extent=start - end, style="arc", outline=color, width=8,
            )

        zone(self.minimum, self.warning, GREEN)
        zone(self.warning, self.danger, YELLOW)
        zone(self.danger, self.maximum, RED)

        tick_outer = radius - 28
        for index in range(51):
            ratio = index / 50.0
            value = self.minimum + ratio * (self.maximum - self.minimum)
            angle = self._angle(value)
            major = index % 5 == 0
            length = 13 if major else 6
            inner = tick_outer - length
            x1 = cx + math.cos(angle) * inner
            y1 = cy - math.sin(angle) * inner
            x2 = cx + math.cos(angle) * tick_outer
            y2 = cy - math.sin(angle) * tick_outer
            tick_color = TEXT if value < self.warning else (YELLOW if value < self.danger else RED)
            self.create_line(x1, y1, x2, y2, fill=tick_color, width=2 if major else 1)
            if major:
                label_radius = inner - 14
                label = value / 1000 if self.maximum >= 1000 else value
                digits = 0 if abs(label) >= 10 else 1
                self.create_text(
                    cx + math.cos(angle) * label_radius,
                    cy - math.sin(angle) * label_radius,
                    text=f"{label:.{digits}f}", fill=MUTED, font=("Segoe UI", 8, "bold"),
                )

        angle = self._angle(self.value)
        needle = radius - 54
        nx = cx + math.cos(angle) * needle
        ny = cy - math.sin(angle) * needle
        self.create_line(cx, cy, nx, ny, fill=ORANGE, width=5, arrow="last", arrowshape=(10, 12, 4))
        self.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, fill="#D9E0E6", outline="#070A0E", width=2)
        self.create_text(cx, cy + radius * 0.33, text=self.title, fill=TEXT, font=("Segoe UI", 10, "bold"))
        self.create_rectangle(
            cx - 58, cy + radius * 0.45, cx + 58, cy + radius * 0.70,
            fill="#05080C", outline=ORANGE_DARK,
        )
        value_text = f"{self.value:.0f}" if abs(self.value) >= 100 else f"{self.value:.1f}"
        self.create_text(cx, cy + radius * 0.56, text=value_text, fill=ORANGE_LIGHT, font=("Consolas", 15, "bold"))
        self.create_text(cx, cy + radius * 0.76, text=self.unit, fill=MUTED, font=("Segoe UI", 8))
        signal_color = GREEN if self.signal else "#4A5664"
        self.create_oval(
            cx + radius * 0.50, cy - radius * 0.52,
            cx + radius * 0.62, cy - radius * 0.40,
            fill=signal_color, outline="",
        )
        self.create_text(cx + radius * 0.35, cy - radius * 0.46, text="RX", fill=MUTED, font=("Segoe UI", 7, "bold"))


class ScopeCanvas(tk.Canvas):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, bg="#05090E", highlightthickness=1, highlightbackground="#3A4655", **kwargs)
        self.samples: deque[float] = deque(maxlen=500)
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
        width = max(480, self.winfo_width())
        height = max(320, self.winfo_height())
        margin = 46
        for index in range(11):
            x = margin + (width - 2 * margin) * index / 10
            self.create_line(x, margin, x, height - margin, fill=GRID)
        for index in range(9):
            y = margin + (height - 2 * margin) * index / 8
            self.create_line(margin, y, width - margin, y, fill=GRID)
        self.create_text(margin, 20, anchor="w", text=f"{self.title} [{self.unit}]", fill=TEXT, font=("Segoe UI", 12, "bold"))
        self.create_text(width - margin, 20, anchor="e", text="TELEMETRÍA ECU · NO ES FORMA DE ONDA ELÉCTRICA", fill=ORANGE, font=("Segoe UI", 9, "bold"))
        if len(self.samples) < 2:
            self.create_text(width / 2, height / 2, text="Esperando muestras OBD-II...", fill=MUTED, font=("Segoe UI", 13))
            return
        values = list(self.samples)
        minimum = min(self.minimum, min(values))
        maximum = max(self.maximum, max(values))
        span = max(maximum - minimum, 0.001)
        points: list[float] = []
        for index, value in enumerate(values):
            x = margin + (width - 2 * margin) * index / max(len(values) - 1, 1)
            y = height - margin - (value - minimum) / span * (height - 2 * margin)
            points.extend((x, y))
        self.create_line(*points, fill=ORANGE, width=3, smooth=False)
        self.create_text(7, margin, anchor="w", text=f"{maximum:.1f}", fill=MUTED, font=("Consolas", 8))
        self.create_text(7, height - margin, anchor="w", text=f"{minimum:.1f}", fill=MUTED, font=("Consolas", 8))


class ScrollFrame(ttk.Frame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, bg=PANEL, highlightthickness=0, width=330)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Panel.TFrame")
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(window, width=event.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class PremiumApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1520x920")
        self.minsize(1220, 760)
        self.configure(bg=BG)
        try:
            self.iconbitmap(resource_path("autoguard.ico"))
        except Exception:
            pass

        self.ui_events: "queue.Queue[tuple]" = queue.Queue()
        self.data_events: "queue.Queue[dict]" = queue.Queue()
        self.client = ELM327Client(log=lambda message: self.ui_events.put(("log", message)))
        self.worker: LiveDataWorker | None = None
        self.database = DtcDatabase()
        self.db_stats = self.database.stats()
        self.supported_pids: set[int] = set()
        self.latest_values: dict[int, float] = {}
        self.min_values: dict[int, float] = {}
        self.max_values: dict[int, float] = {}
        self.history: dict[int, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=900))
        self.current_dtcs: list[dict[str, str]] = []
        self.fuel_source = "No disponible"
        self.scope_samples = 0

        self._configure_style()
        self._build_shell()
        self._show_page("Inicio")
        self.after(80, self._drain_queues)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Panel2.TFrame", background=PANEL_2)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel2.TLabel", background=PANEL_2, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 20, "bold"))
        style.configure("Orange.TLabel", background=BG, foreground=ORANGE, font=("Segoe UI", 10, "bold"))
        style.configure("TButton", background=PANEL_3, foreground=TEXT, padding=(11, 7), font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TButton", background=[("active", "#344253")])
        style.configure("Accent.TButton", background=ORANGE, foreground="white", padding=(12, 8), borderwidth=0)
        style.map("Accent.TButton", background=[("active", ORANGE_LIGHT)])
        style.configure("Treeview", background="#0D141D", fieldbackground="#0D141D", foreground=TEXT, rowheight=28, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#2A3543", foreground=TEXT, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#75400F")])
        style.configure("TEntry", fieldbackground="#0B1118", foreground=TEXT)
        style.configure("TCombobox", fieldbackground="#0B1118", foreground=TEXT)
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", PANEL)])

    def _build_shell(self) -> None:
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, bg=SIDEBAR, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        main = tk.Frame(shell, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self._build_sidebar()
        self._build_header(main)
        self.page_host = tk.Frame(main, bg=BG)
        self.page_host.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.pages: dict[str, tk.Widget] = {}
        self._build_pages()
        self.status_var = tk.StringVar(value="AUTOGUARD listo")
        status = tk.Label(main, textvariable=self.status_var, bg="#070A0E", fg=MUTED, anchor="w", padx=12, pady=6, font=("Segoe UI", 9))
        status.pack(fill="x")

    def _build_sidebar(self) -> None:
        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=15, pady=(18, 22))
        try:
            image = Image.open(resource_path("autoguard.png")).resize((58, 58), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(image)
            tk.Label(brand, image=self.logo, bg=SIDEBAR).pack(side="left")
        except Exception:
            tk.Label(brand, text="A", bg=ORANGE, fg="white", font=("Segoe UI", 24, "bold"), width=3).pack(side="left")
        text = tk.Frame(brand, bg=SIDEBAR)
        text.pack(side="left", padx=10)
        tk.Label(text, text="AUTOGUARD", bg=SIDEBAR, fg=ORANGE, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(text, text="SCAN DIOS v6.2", bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.nav_buttons: dict[str, tk.Button] = {}
        entries = [
            ("Inicio", "⌂"), ("Conexión", "◉"), ("DTC y soluciones", "⚠"),
            ("Datos en vivo", "≋"), ("Osciloscopio", "⌁"),
            ("Pruebas funcionales", "✓"), ("Consola técnica", ">_"),
            ("Informe Premium", "PDF"), ("Información", "i"),
        ]
        for name, icon in entries:
            button = tk.Button(
                self.sidebar, text=f"  {icon}   {name}", anchor="w", relief="flat",
                bg=SIDEBAR, fg=TEXT, activebackground="#1E2A38", activeforeground="white",
                font=("Segoe UI", 10, "bold"), padx=12, pady=10,
                command=lambda page=name: self._show_page(page),
            )
            button.pack(fill="x", padx=8, pady=1)
            self.nav_buttons[name] = button

        footer = tk.Frame(self.sidebar, bg=SIDEBAR)
        footer.pack(side="bottom", fill="x", padx=15, pady=15)
        self.side_connection = tk.Label(footer, text="● SIN CONEXIÓN", bg=SIDEBAR, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.side_connection.pack(anchor="w")
        tk.Label(footer, text=f"Autor: {APP_AUTHOR}", bg=SIDEBAR, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

    def _build_header(self, parent) -> None:
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", padx=17, pady=12)
        left = tk.Frame(header, bg=BG)
        left.pack(side="left")
        tk.Label(left, text=APP_NAME, bg=BG, fg=TEXT, font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(left, text=f"v{APP_VERSION} · {APP_BUILD}", bg=BG, fg=ORANGE, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        self.header_protocol = tk.Label(right, text="Protocolo: sin conexión", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.header_protocol.pack(anchor="e")
        self.header_status = tk.Label(right, text="● DESCONECTADO", bg=BG, fg=MUTED, font=("Segoe UI", 10, "bold"))
        self.header_status.pack(anchor="e", pady=(3, 0))

    def _new_page(self, name: str) -> tk.Frame:
        page = tk.Frame(self.page_host, bg=BG)
        page.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.pages[name] = page
        return page

    def _build_pages(self) -> None:
        self._build_home(self._new_page("Inicio"))
        self._build_connection(self._new_page("Conexión"))
        self._build_dtc(self._new_page("DTC y soluciones"))
        self._build_live(self._new_page("Datos en vivo"))
        self._build_scope(self._new_page("Osciloscopio"))
        self._build_tests(self._new_page("Pruebas funcionales"))
        self._build_console(self._new_page("Consola técnica"))
        self._build_report(self._new_page("Informe Premium"))
        self._build_info(self._new_page("Información"))

    def _show_page(self, name: str) -> None:
        self.pages[name].tkraise()
        for page, button in self.nav_buttons.items():
            selected = page == name
            button.configure(bg="#40240C" if selected else SIDEBAR, fg=ORANGE_LIGHT if selected else TEXT)

    def _card(self, parent, title: str, value: str = "", subtitle: str = "") -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground="#334151", highlightthickness=1)
        tk.Label(frame, text=title.upper(), bg=PANEL_2, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        value_label = tk.Label(frame, text=value, bg=PANEL_2, fg=ORANGE, font=("Segoe UI", 15, "bold"))
        value_label.pack(anchor="w", padx=12)
        if subtitle:
            tk.Label(frame, text=subtitle, bg=PANEL_2, fg=MUTED, font=("Segoe UI", 8), wraplength=250, justify="left").pack(anchor="w", padx=12, pady=(2, 10))
        frame.value_label = value_label  # type: ignore[attr-defined]
        return frame

    def _section_title(self, parent, title: str, subtitle: str = "") -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(2, 10))
        tk.Label(row, text=title, bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(row, text=subtitle, bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

    def _build_home(self, page: tk.Frame) -> None:
        self._section_title(page, "Panel principal DIOS", "Telemetría, estado del vehículo y acceso rápido")
        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="x")
        for column in range(4):
            cards.columnconfigure(column, weight=1)
        self.card_connection = self._card(cards, "Conexión", "Desconectado", "ELM327 por COM, WiFi o simulador")
        self.card_protocol = self._card(cards, "Protocolo", "Sin detectar", "Detección automática OBD-II")
        self.card_dtc = self._card(cards, "DTC de sesión", "0", "Confirmados, pendientes y permanentes")
        self.card_database = self._card(
            cards, "Base offline", f"{self.db_stats['unique_codes']:,}".replace(",", "."),
            f"{self.db_stats.get('solutions', 0):,} planes técnicos".replace(",", "."),
        )
        for index, card in enumerate((self.card_connection, self.card_protocol, self.card_dtc, self.card_database)):
            card.grid(row=0, column=index, padx=(0 if index == 0 else 6, 0 if index == 3 else 6), sticky="nsew")

        gauges = tk.Frame(page, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        gauges.pack(fill="x", pady=12)
        for column in range(4):
            gauges.columnconfigure(column, weight=1)
        self.gauge_rpm = Gauge(gauges, "RPM", "rpm", 0, 7000, 4800, 6200)
        self.gauge_speed = Gauge(gauges, "VELOCIDAD", "km/h", 0, 240, 160, 210)
        self.gauge_temp = Gauge(gauges, "REFRIGERANTE", "°C", 40, 130, 100, 115)
        self.gauge_voltage = Gauge(gauges, "BATERÍA", "V", 8, 18, 15.2, 16.5)
        for index, gauge in enumerate((self.gauge_rpm, self.gauge_speed, self.gauge_temp, self.gauge_voltage)):
            gauge.grid(row=0, column=index, sticky="nsew", padx=5, pady=5)

        lower = tk.Frame(page, bg=BG)
        lower.pack(fill="both", expand=True)
        lower.columnconfigure(0, weight=3)
        lower.columnconfigure(1, weight=2)
        live_panel = tk.Frame(lower, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        live_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        console_panel = tk.Frame(lower, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        console_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(live_panel, text="DATOS EN VIVO DESTACADOS", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=9)
        self.home_live = ttk.Treeview(live_panel, columns=("parameter", "value", "unit", "pid"), show="headings", height=7)
        for column, title, width in (("parameter", "Parámetro", 280), ("value", "Valor", 100), ("unit", "Unidad", 80), ("pid", "PID", 75)):
            self.home_live.heading(column, text=title)
            self.home_live.column(column, width=width, anchor="w")
        self.home_live.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.home_items: dict[int, str] = {}
        for pid in (0x0C, 0x0D, 0x05, 0x42, 0x2F, 0x5E):
            name, unit = PID_DEFINITIONS[pid]
            self.home_items[pid] = self.home_live.insert("", "end", values=(name, "--", unit, f"01{pid:02X}"))

        tk.Label(console_panel, text="CONSOLA TÉCNICA", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=9)
        self.home_console = tk.Text(console_panel, bg="#05090D", fg="#72E39A", insertbackground=TEXT, relief="flat", font=("Consolas", 9), height=8)
        self.home_console.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.home_console.insert("end", "AUTOGUARD listo. Conecte un adaptador o use el simulador.\n")

    def _build_connection(self, page: tk.Frame) -> None:
        self._section_title(page, "Conexión OBD-II", "Detección automática mediante ELM327")
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        form = tk.Frame(body, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        form.pack(side="left", fill="both", expand=True, padx=(0, 8))
        info = tk.Frame(body, bg=PANEL_2, highlightbackground="#303E4D", highlightthickness=1, width=360)
        info.pack(side="left", fill="y", padx=(8, 0))
        info.pack_propagate(False)
        self.mode_var = tk.StringVar(value="Simulador")
        self.com_var = tk.StringVar(value="COM3")
        self.baud_var = tk.StringVar(value="38400")
        self.host_var = tk.StringVar(value="192.168.0.10")
        self.wifi_port_var = tk.StringVar(value="35000")
        self.timeout_var = tk.StringVar(value="2.0")
        fields = [
            ("Modo", self.mode_var, ["Simulador", "COM", "WiFi"]),
            ("Puerto COM", self.com_var, ELM327Client.available_serial_ports()),
            ("Baudrate", self.baud_var, None), ("Host WiFi", self.host_var, None),
            ("Puerto WiFi", self.wifi_port_var, None), ("Timeout", self.timeout_var, None),
        ]
        for row, (label, variable, options) in enumerate(fields):
            tk.Label(form, text=label, bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", padx=18, pady=10)
            if options is not None:
                widget = ttk.Combobox(form, textvariable=variable, values=options, state="readonly" if row == 0 else "normal", width=38)
                if row == 1:
                    self.com_combo = widget
            else:
                widget = ttk.Entry(form, textvariable=variable, width=40)
            widget.grid(row=row, column=1, sticky="ew", padx=18, pady=10)
        form.columnconfigure(1, weight=1)
        buttons = tk.Frame(form, bg=PANEL)
        buttons.grid(row=6, column=0, columnspan=2, sticky="w", padx=18, pady=18)
        ttk.Button(buttons, text="Actualizar puertos", command=self._refresh_ports).pack(side="left", padx=(0, 8))
        self.connect_button = ttk.Button(buttons, text="Conectar", style="Accent.TButton", command=self._connect)
        self.connect_button.pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Desconectar", command=self._disconnect).pack(side="left")
        self.connection_detail = tk.Label(form, text="Estado: sin conexión", bg=PANEL, fg=MUTED, font=("Segoe UI", 10, "bold"))
        self.connection_detail.grid(row=7, column=0, columnspan=2, sticky="w", padx=18, pady=10)
        tk.Label(info, text="CONEXIÓN PROFESIONAL", bg=PANEL_2, fg=ORANGE, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(20, 12))
        connection_text = (
            "• WiFi: use IP y puerto configurados en el ELM327.\n\n"
            "• COM: seleccione el puerto Bluetooth o USB.\n\n"
            "• Simulador: valida interfaz, sensores, DTC, gráficos e informe sin vehículo.\n\n"
            "La aplicación consulta los bloques 0100, 0120, 0140 y 0160 para mostrar solo los PID anunciados por la ECU."
        )
        tk.Label(info, text=connection_text, bg=PANEL_2, fg=TEXT, justify="left", wraplength=320, font=("Segoe UI", 10)).pack(anchor="nw", padx=18)

    def _build_dtc(self, page: tk.Frame) -> None:
        self._section_title(page, "DTC y base offline de soluciones", "Códigos P, B, C y U con procedimientos paso a paso")
        toolbar = tk.Frame(page, bg=BG)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Escaneo completo", style="Accent.TButton", command=self._scan_dtcs).pack(side="left", padx=(0, 7))
        ttk.Button(toolbar, text="Borrar DTC", command=self._clear_dtcs).pack(side="left", padx=(0, 16))
        tk.Label(toolbar, text="Código o descripción:", bg=BG, fg=TEXT).pack(side="left")
        self.dtc_search_var = tk.StringVar(value="U0123")
        entry = ttk.Entry(toolbar, textvariable=self.dtc_search_var, width=24)
        entry.pack(side="left", padx=7)
        entry.bind("<Return>", lambda _event: self._search_dtc())
        ttk.Button(toolbar, text="Buscar en base", command=self._search_dtc).pack(side="left")
        self.dtc_count_label = tk.Label(toolbar, text="", bg=BG, fg=MUTED)
        self.dtc_count_label.pack(side="right")

        split = tk.PanedWindow(page, orient="vertical", bg=BG, sashwidth=6, sashrelief="flat")
        split.pack(fill="both", expand=True)
        table_frame = tk.Frame(split, bg=PANEL)
        solution_frame = tk.Frame(split, bg=PANEL)
        split.add(table_frame, minsize=260)
        split.add(solution_frame, minsize=260)
        columns = ("code", "status", "description", "manufacturer", "type")
        self.dtc_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "code": ("Código", 90), "status": ("Estado", 105), "description": ("Descripción", 600),
            "manufacturer": ("Fabricante", 150), "type": ("Tipo", 95),
        }
        for column, (title, width) in headings.items():
            self.dtc_tree.heading(column, text=title)
            self.dtc_tree.column(column, width=width, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.dtc_tree.yview)
        self.dtc_tree.configure(yscrollcommand=scroll.set)
        self.dtc_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.dtc_tree.bind("<<TreeviewSelect>>", self._show_selected_solution)
        tk.Label(solution_frame, text="PLAN DE ACCIÓN OFFLINE", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=8)
        self.solution_text = tk.Text(solution_frame, bg="#070C12", fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10), wrap="word")
        solution_scroll = ttk.Scrollbar(solution_frame, orient="vertical", command=self.solution_text.yview)
        self.solution_text.configure(yscrollcommand=solution_scroll.set)
        self.solution_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        solution_scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))
        self.solution_text.insert("end", "Seleccione un código para consultar causas, síntomas, pasos, herramientas y validación.")

    def _build_live(self, page: tk.Frame) -> None:
        self._section_title(page, "Datos en vivo", "Lectura de todos los sensores estándar anunciados por la ECU")
        wrapper = tk.Frame(page, bg=BG)
        wrapper.pack(fill="both", expand=True)
        left = tk.Frame(wrapper, bg=PANEL, width=355, highlightbackground="#303E4D", highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        right = tk.Frame(wrapper, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(left, text="SENSORES SELECCIONABLES", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=10)
        controls = tk.Frame(left, bg=PANEL)
        controls.pack(fill="x", padx=10)
        ttk.Button(controls, text="Soportados", command=self._select_supported).pack(side="left", padx=(0, 4))
        ttk.Button(controls, text="Todos", command=lambda: self._set_all_pids(True)).pack(side="left", padx=4)
        ttk.Button(controls, text="Limpiar", command=lambda: self._set_all_pids(False)).pack(side="left", padx=4)
        scroll = ScrollFrame(left, style="Panel.TFrame")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)
        self.pid_vars: dict[int, tk.BooleanVar] = {}
        defaults = {0x0C, 0x0D, 0x05, 0x42, 0x10, 0x2F, 0x5E}
        for pid, (name, unit) in PID_DEFINITIONS.items():
            var = tk.BooleanVar(value=pid in defaults)
            self.pid_vars[pid] = var
            ttk.Checkbutton(scroll.inner, text=f"{name} [{unit}] · 01{pid:02X}", variable=var).pack(anchor="w", padx=6, pady=3)
        buttons = tk.Frame(left, bg=PANEL)
        buttons.pack(fill="x", padx=10, pady=(4, 10))
        ttk.Button(buttons, text="Iniciar lectura", style="Accent.TButton", command=self._start_live).pack(fill="x", pady=(0, 5))
        ttk.Button(buttons, text="Detener", command=self._stop_live).pack(fill="x")
        self.fuel_source_label = tk.Label(left, text="Flujómetro: no disponible", bg=PANEL, fg=ORANGE_LIGHT, wraplength=320, justify="left", font=("Segoe UI", 9, "bold"))
        self.fuel_source_label.pack(anchor="w", padx=12, pady=(2, 12))

        columns = ("parameter", "value", "unit", "minimum", "maximum", "pid")
        self.live_tree = ttk.Treeview(right, columns=columns, show="headings")
        for column, title, width in (
            ("parameter", "Parámetro", 300), ("value", "Actual", 100), ("unit", "Unidad", 80),
            ("minimum", "Mínimo", 100), ("maximum", "Máximo", 100), ("pid", "PID", 75),
        ):
            self.live_tree.heading(column, text=title)
            self.live_tree.column(column, width=width, anchor="w")
        live_scroll = ttk.Scrollbar(right, orient="vertical", command=self.live_tree.yview)
        self.live_tree.configure(yscrollcommand=live_scroll.set)
        self.live_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        live_scroll.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.live_items: dict[int, str] = {}
        for pid, (name, unit) in PID_DEFINITIONS.items():
            self.live_items[pid] = self.live_tree.insert("", "end", values=(name, "--", unit, "--", "--", f"01{pid:02X}"))

    def _build_scope(self, page: tk.Frame) -> None:
        self._section_title(page, "Osciloscopio de telemetría", "Gráfico continuo de cualquier PID soportado")
        toolbar = tk.Frame(page, bg=BG)
        toolbar.pack(fill="x", pady=(0, 8))
        tk.Label(toolbar, text="Señal ECU:", bg=BG, fg=TEXT).pack(side="left")
        self.scope_name_to_pid = {f"{name} [{unit}]": pid for pid, (name, unit) in PID_DEFINITIONS.items()}
        self.scope_var = tk.StringVar(value="RPM del motor [rpm]")
        ttk.Combobox(toolbar, textvariable=self.scope_var, values=list(self.scope_name_to_pid), state="readonly", width=43).pack(side="left", padx=7)
        ttk.Button(toolbar, text="Iniciar", style="Accent.TButton", command=self._start_scope).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Detener", command=self._stop_live).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Exportar CSV", command=self._export_scope_csv).pack(side="left")
        self.scope_rate = tk.Label(toolbar, text="0 muestras", bg=BG, fg=MUTED)
        self.scope_rate.pack(side="right")
        self.scope_canvas = ScopeCanvas(page, height=590)
        self.scope_canvas.pack(fill="both", expand=True)
        tk.Label(
            page,
            text="La gráfica representa datos calculados y transmitidos por la ECU. Señales eléctricas CKP, CMP, bobinas, inyectores y CAN requieren un osciloscopio físico.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=1100, justify="left",
        ).pack(anchor="w", pady=(8, 0))

    def _build_tests(self, page: tk.Frame) -> None:
        self._section_title(page, "Pruebas funcionales guiadas", "Procedimientos responsables para validar el diagnóstico")
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        self.test_list = tk.Listbox(body, bg=PANEL, fg=TEXT, selectbackground=ORANGE_DARK, relief="flat", font=("Segoe UI", 10), width=42)
        self.test_list.pack(side="left", fill="y", padx=(0, 8))
        tests = [
            "Voltaje, batería y carga", "RPM y acelerador", "MAF/MAP bajo carga",
            "Nivel y flujo de combustible", "Temperatura y termostato", "Trims de combustible",
            "Monitores de emisiones", "Prueba de ruta controlada",
        ]
        for test in tests:
            self.test_list.insert("end", test)
        self.test_list.selection_set(0)
        self.test_list.bind("<<ListboxSelect>>", self._show_test)
        self.test_text = tk.Text(body, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 11))
        self.test_text.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self._show_test()

    def _build_console(self, page: tk.Frame) -> None:
        self._section_title(page, "Consola técnica ELM327", "Comandos manuales para técnicos con conocimiento del protocolo")
        self.console_text = tk.Text(page, bg="#04080C", fg="#70E39B", insertbackground=TEXT, relief="flat", font=("Consolas", 10))
        self.console_text.pack(fill="both", expand=True)
        command = tk.Frame(page, bg=BG)
        command.pack(fill="x", pady=(8, 0))
        self.console_command_var = tk.StringVar(value="ATI")
        ttk.Entry(command, textvariable=self.console_command_var).pack(side="left", fill="x", expand=True)
        ttk.Button(command, text="Enviar comando", style="Accent.TButton", command=self._send_console).pack(side="left", padx=(8, 0))
        ttk.Button(command, text="Limpiar", command=lambda: self.console_text.delete("1.0", "end")).pack(side="left", padx=(8, 0))

    def _build_report(self, page: tk.Frame) -> None:
        self._section_title(page, "Informe PDF Premium", "Gráficos, DTC, soluciones y plan de acción paso a paso")
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        form = tk.Frame(body, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        form.pack(side="left", fill="y", padx=(0, 8))
        notes = tk.Frame(body, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        notes.pack(side="left", fill="both", expand=True, padx=(8, 0))
        fields = ["cliente", "patente", "marca", "modelo", "anio", "vin", "kilometraje", "motor", "tecnico"]
        labels = ["Cliente", "Patente", "Marca", "Modelo", "Año", "VIN", "Kilometraje", "Motor", "Técnico"]
        self.report_vars: dict[str, tk.StringVar] = {}
        for row, (key, label) in enumerate(zip(fields, labels)):
            variable = tk.StringVar(value=APP_AUTHOR if key == "tecnico" else "")
            self.report_vars[key] = variable
            tk.Label(form, text=label, bg=PANEL, fg=TEXT, font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", padx=14, pady=6)
            ttk.Entry(form, textvariable=variable, width=34).grid(row=row, column=1, padx=14, pady=6)
        tk.Label(notes, text="OBSERVACIONES, DIAGNÓSTICO Y RECOMENDACIONES", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=10)
        self.report_notes = tk.Text(notes, bg="#070C12", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 10))
        self.report_notes.pack(fill="both", expand=True, padx=10)
        self.report_notes.insert("end", "Registrar aquí síntomas, condiciones de prueba, mediciones confirmatorias y recomendaciones del técnico.")
        footer = tk.Frame(notes, bg=PANEL)
        footer.pack(fill="x", padx=10, pady=10)
        ttk.Button(footer, text="Generar informe PDF Premium", style="Accent.TButton", command=self._generate_report).pack(side="left")
        self.report_status = tk.Label(footer, text="El informe incluirá gráficos de la sesión y planes DTC.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.report_status.pack(side="left", padx=12)

    def _build_info(self, page: tk.Frame) -> None:
        self._section_title(page, "Información y planificación", "Datos de la aplicación, cobertura y checklist técnico")
        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="x")
        for column in range(4):
            cards.columnconfigure(column, weight=1)
        info_cards = [
            self._card(cards, "Versión instalada", APP_VERSION, APP_BUILD),
            self._card(cards, "Autor", APP_AUTHOR, "Desarrollador y fundador AUTOGUARD"),
            self._card(cards, "Base DTC", f"{self.db_stats['unique_codes']:,}".replace(",", "."), f"{self.db_stats['definitions']:,} definiciones".replace(",", ".")),
            self._card(cards, "Soluciones offline", f"{self.db_stats.get('solutions', 0):,}".replace(",", "."), "Causas, pasos, herramientas y validación"),
        ]
        for index, card in enumerate(info_cards):
            card.grid(row=0, column=index, padx=(0 if index == 0 else 6, 0 if index == 3 else 6), sticky="nsew")
        middle = tk.Frame(page, bg=BG)
        middle.pack(fill="both", expand=True, pady=12)
        features = tk.Frame(middle, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        features.pack(side="left", fill="both", expand=True, padx=(0, 6))
        planning = tk.Frame(middle, bg=PANEL, highlightbackground="#303E4D", highlightthickness=1)
        planning.pack(side="left", fill="both", expand=True, padx=(6, 0))
        tk.Label(features, text="FUNCIONES PRINCIPALES", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=10)
        feature_text = (
            "✓ ELM327 por WiFi, COM y simulador\n\n"
            "✓ Detección automática de protocolo y PID soportados\n\n"
            "✓ DTC confirmados, pendientes y permanentes\n\n"
            "✓ Base offline P/B/C/U y planes de acción\n\n"
            "✓ Flujómetro PID 015E y estimación MAF identificada\n\n"
            "✓ Nivel de combustible PID 012F\n\n"
            "✓ Osciloscopio de telemetría ECU\n\n"
            "✓ Informe PDF Premium con gráficos y soluciones"
        )
        tk.Label(features, text=feature_text, bg=PANEL, fg=TEXT, justify="left", font=("Segoe UI", 10)).pack(anchor="nw", padx=14)
        tk.Label(planning, text="HOJA DE PLANIFICACIÓN TÉCNICA", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=10)
        columns = ("task", "priority", "status")
        self.plan_tree = ttk.Treeview(planning, columns=columns, show="headings", height=10)
        for column, title, width in (("task", "Tarea", 310), ("priority", "Prioridad", 90), ("status", "Estado", 110)):
            self.plan_tree.heading(column, text=title)
            self.plan_tree.column(column, width=width, anchor="w")
        for task, priority, status in (
            ("Conectar y validar comunicación ECU", "Alta", "Pendiente"),
            ("Guardar DTC y freeze frame", "Alta", "Pendiente"),
            ("Seleccionar PID relacionados", "Alta", "Pendiente"),
            ("Registrar gráficos y condiciones", "Media", "Pendiente"),
            ("Consultar plan de acción offline", "Media", "Pendiente"),
            ("Confirmar con mediciones y OEM", "Alta", "Pendiente"),
            ("Generar informe Premium", "Media", "Pendiente"),
        ):
            self.plan_tree.insert("", "end", values=(task, priority, status))
        self.plan_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _refresh_ports(self) -> None:
        ports = ELM327Client.available_serial_ports()
        self.com_combo.configure(values=ports)
        if ports:
            self.com_var.set(ports[0])
        self._set_status(f"Puertos detectados: {len(ports)}")

    def _connection_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            mode=self.mode_var.get(), serial_port=self.com_var.get(), baudrate=int(self.baud_var.get()),
            wifi_host=self.host_var.get(), wifi_port=int(self.wifi_port_var.get()), timeout=float(self.timeout_var.get()),
        )

    def _connect(self) -> None:
        self.connect_button.configure(state="disabled")
        self._set_status("Conectando e identificando PIDs...")
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
        self.supported_pids.clear()
        self.header_status.configure(text="● DESCONECTADO", fg=MUTED)
        self.header_protocol.configure(text="Protocolo: sin conexión")
        self.side_connection.configure(text="● SIN CONEXIÓN", fg=MUTED)
        self.connection_detail.configure(text="Estado: sin conexión", fg=MUTED)
        self.card_connection.value_label.configure(text="Desconectado")  # type: ignore[attr-defined]
        self.card_protocol.value_label.configure(text="Sin detectar")  # type: ignore[attr-defined]
        self._set_status("Desconectado")

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
        if not messagebox.askyesno("Borrar DTC", "¿Confirma el borrado después de guardar la evidencia?"):
            return
        def task() -> None:
            try:
                ok = self.client.clear_dtcs()
                self.ui_events.put(("info", "Borrar DTC", "La ECU confirmó el borrado." if ok else "La ECU no confirmó el borrado."))
            except Exception as exc:
                self.ui_events.put(("error", "Borrar DTC", str(exc)))
        threading.Thread(target=task, daemon=True).start()

    def _populate_dtc_tree(self, records: list[tuple[DTCRecord, str]]) -> None:
        for item in self.dtc_tree.get_children():
            self.dtc_tree.delete(item)
        self.current_dtcs.clear()
        for record, status in records:
            item = self.dtc_tree.insert("", "end", values=(
                record.code, status, record.description, record.manufacturer,
                "Genérico" if record.is_generic else "Específico",
            ))
            self.current_dtcs.append({
                "code": record.code, "status": status, "description": record.description,
                "manufacturer": record.manufacturer, "tree_item": item,
            })
        self.dtc_count_label.configure(text=f"{len(records)} definiciones")
        self.card_dtc.value_label.configure(text=str(len({item['code'] for item in self.current_dtcs})))  # type: ignore[attr-defined]
        if records:
            first = self.dtc_tree.get_children()[0]
            self.dtc_tree.selection_set(first)
            self.dtc_tree.focus(first)
            self._show_selected_solution()

    def _search_dtc(self) -> None:
        query = self.dtc_search_var.get().strip()
        if not query:
            return
        records = self.database.search(query, limit=400)
        self._populate_dtc_tree([(record, "Base offline") for record in records])
        self._set_status(f"Búsqueda DTC: {len(records)} resultados")

    def _show_selected_solution(self, _event=None) -> None:
        selection = self.dtc_tree.selection()
        if not selection:
            return
        values = self.dtc_tree.item(selection[0], "values")
        if not values:
            return
        code, _status, description, manufacturer, _type = values
        solution = self.database.solution(str(code), str(manufacturer))
        self.solution_text.delete("1.0", "end")
        self.solution_text.insert("end", f"{code} · {description}\n", "title")
        if solution is None:
            self.solution_text.insert("end", "No existe plan offline para esta definición. Confirmar con información OEM.")
            return
        sections = [
            ("SISTEMA", solution.system), ("SEVERIDAD", solution.severity),
            ("SÍNTOMAS PROBABLES", solution.symptoms), ("CAUSAS PROBABLES", solution.causes),
            ("PROCESO PASO A PASO", solution.steps), ("SENSORES RELACIONADOS", solution.sensors),
            ("HERRAMIENTAS", solution.tools), ("VALIDACIÓN FINAL", solution.validation),
        ]
        for title, text in sections:
            self.solution_text.insert("end", f"\n{title}\n", "heading")
            self.solution_text.insert("end", f"{text}\n")
        self.solution_text.tag_configure("title", foreground=ORANGE, font=("Segoe UI", 13, "bold"))
        self.solution_text.tag_configure("heading", foreground=ORANGE_LIGHT, font=("Segoe UI", 10, "bold"))

    def _set_all_pids(self, value: bool) -> None:
        for variable in self.pid_vars.values():
            variable.set(value)

    def _select_supported(self) -> None:
        if not self.supported_pids:
            messagebox.showinfo("Sensores", "Conecte primero la ECU para detectar PIDs soportados.")
            return
        for pid, variable in self.pid_vars.items():
            variable.set(pid in self.supported_pids)
        self._set_status(f"Seleccionados {len(self.supported_pids & set(PID_DEFINITIONS))} PID implementados y soportados")

    def _selected_pids(self) -> list[int]:
        selected = [pid for pid, variable in self.pid_vars.items() if variable.get()]
        if self.supported_pids and not self.mode_var.get().lower().startswith("sim"):
            selected = [pid for pid in selected if pid in self.supported_pids]
        return selected

    def _restart_worker(self, pids: list[int]) -> None:
        self._stop_live(update_status=False)
        if not self.client.connected:
            raise RuntimeError("No existe conexión activa")
        if not pids:
            raise RuntimeError("Seleccione al menos un PID soportado")
        self.worker = LiveDataWorker(self.client, pids, self.data_events)
        self.worker.start()
        self._set_status(f"Datos en vivo activos · {len(pids)} PID")

    def _start_live(self) -> None:
        try:
            self._restart_worker(self._selected_pids())
        except Exception as exc:
            messagebox.showwarning("Datos en vivo", str(exc))

    def _start_scope(self) -> None:
        pid = self.scope_name_to_pid.get(self.scope_var.get(), 0x0C)
        name, unit = PID_DEFINITIONS[pid]
        minimum, maximum = PID_RANGES.get(pid, (0, 100))
        self.scope_canvas.configure_signal(name, unit, minimum, maximum)
        self.scope_samples = 0
        selected = list(dict.fromkeys(self._selected_pids() + [pid]))
        try:
            self._restart_worker(selected)
        except Exception as exc:
            messagebox.showwarning("Osciloscopio", str(exc))

    def _stop_live(self, update_status: bool = True) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker.join(timeout=1.0)
            self.worker = None
        if update_status:
            self._set_status("Datos en vivo detenidos")

    def _export_scope_csv(self) -> None:
        pid = self.scope_name_to_pid.get(self.scope_var.get(), 0x0C)
        samples = list(self.history.get(pid, []))
        if not samples:
            messagebox.showinfo("Exportar CSV", "No existen muestras para exportar.")
            return
        name, unit = PID_DEFINITIONS[pid]
        target = filedialog.asksaveasfilename(title="Exportar telemetría", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile=f"AUTOGUARD_{pid:02X}.csv")
        if not target:
            return
        with open(target, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["timestamp", "pid", "parametro", "valor", "unidad"])
            for timestamp, value in samples:
                writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)), f"01{pid:02X}", name, f"{value:.4f}", unit])
        self._set_status(f"CSV exportado: {target}")

    def _show_test(self, _event=None) -> None:
        selected = self.test_list.curselection()
        index = selected[0] if selected else 0
        guides = [
            "VERIFICACIÓN DE VOLTAJE, BATERÍA Y CARGA\n\n1. Motor apagado: mida batería en reposo.\n2. Durante arranque: observe caída de tensión.\n3. Motor en marcha: compare PID 0142 con multímetro.\n4. Aplique cargas eléctricas y confirme estabilidad.\n5. Revise masas y caída de tensión si existen diferencias.\n\nConfirme rangos OEM antes de concluir.",
            "RESPUESTA DE RPM Y ACELERADOR\n\n1. Motor a temperatura de operación.\n2. Registre RPM, carga y posiciones de acelerador/pedal.\n3. Acelere progresivamente sin carga.\n4. Compruebe continuidad y ausencia de saltos.\n5. Confirme retorno estable al ralentí.",
            "RESPUESTA MAF/MAP BAJO CARGA\n\n1. Revise filtro, ductos y fugas.\n2. Registre MAF y MAP en ralentí.\n3. Registre durante aceleración controlada.\n4. Compare tendencia con RPM, carga y trims.\n5. Confirme con especificación según cilindrada y sobrealimentación.",
            "NIVEL Y FLUJO DE COMBUSTIBLE\n\n1. Verifique si la ECU anuncia PID 012F y 015E.\n2. Compare nivel con tablero y condición física.\n3. Compare flujo directo 015E con estimación MAF.\n4. Registre diferencias bajo ralentí y carga.\n5. La estimación MAF no reemplaza un flujómetro físico ni una prueba de presión/caudal.",
            "TEMPERATURA Y TERMOSTATO\n\n1. Inicie con motor frío.\n2. Registre ECT, IAT y temperatura ambiente.\n3. Observe aumento continuo.\n4. Confirme estabilización al abrir termostato.\n5. Verifique ventilador según estrategia OEM.\n\nNo abra el circuito en caliente.",
            "TRIMS DE COMBUSTIBLE\n\n1. Registre STFT/LTFT por banco en ralentí.\n2. Compare a 2500 RPM y bajo carga controlada.\n3. Correlacione con MAF, MAP, O2/A/F y presión de combustible.\n4. Busque fugas o restricciones antes de sustituir sensores.\n5. Confirme adaptativos tras reparación.",
            "MONITORES DE EMISIONES\n\n1. Lea monitores antes de borrar DTC.\n2. Guarde pendientes y permanentes.\n3. Repare la causa confirmada.\n4. Realice ciclo de conducción OEM.\n5. Reescanee sin borrar evidencia.",
            "PRUEBA DE RUTA CONTROLADA\n\n1. Defina ruta y condiciones seguras.\n2. Use acompañante para operar el computador.\n3. Registre PID relacionados.\n4. Marque el momento del síntoma.\n5. Detenga el vehículo antes de revisar datos.\n6. Reescanee al finalizar.\n\nNunca opere el computador mientras conduce.",
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

    def _report_dtc_payload(self) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in self.current_dtcs:
            key = (item["code"], item["manufacturer"])
            if key in seen:
                continue
            seen.add(key)
            solution = self.database.solution(item["code"], item["manufacturer"])
            enriched = dict(item)
            if solution:
                enriched.update({
                    "system": solution.system, "severity": solution.severity,
                    "symptoms": solution.symptoms, "causes": solution.causes,
                    "steps": solution.steps, "validation": solution.validation,
                    "sensors": solution.sensors, "tools": solution.tools,
                })
            payload.append(enriched)
        return payload

    def _generate_report(self) -> None:
        suggested = default_report_path()
        target = filedialog.asksaveasfilename(
            title="Guardar informe Premium AUTOGUARD", defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")], initialfile=suggested.name, initialdir=str(suggested.parent),
        )
        if not target:
            return
        output = Path(target)
        vehicle = {key: variable.get() for key, variable in self.report_vars.items()}
        live: dict[str, str] = {}
        for pid, value in self.latest_values.items():
            if pid in PID_DEFINITIONS:
                name, unit = PID_DEFINITIONS[pid]
                live[name] = f"{value:.2f} {unit}"
        live["Origen flujómetro"] = self.fuel_source
        history: dict[str, list[tuple[float, float]]] = {}
        priority = (0x0C, 0x0D, 0x05, 0x42, 0x10, 0x2F, 0x5E, 0x06, 0x07)
        for pid in priority:
            samples = list(self.history.get(pid, []))
            if samples:
                name, unit = PID_DEFINITIONS[pid]
                history[f"{name} [{unit}]"] = samples
        try:
            generate_pdf_report(
                output, vehicle=vehicle, protocol=self.client.protocol,
                dtcs=self._report_dtc_payload(), live_values=live, history=history,
                notes=self.report_notes.get("1.0", "end").strip(),
                author=vehicle.get("tecnico") or APP_AUTHOR, version=APP_VERSION,
            )
            self.report_status.configure(text=f"Informe creado: {output}", fg=GREEN)
            if messagebox.askyesno("Informe creado", "El informe Premium se creó correctamente. ¿Desea abrirlo?"):
                open_path(output)
        except Exception as exc:
            messagebox.showerror("Informe PDF", str(exc))

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _append_console(self, text: str) -> None:
        line = text.rstrip() + "\n"
        self.console_text.insert("end", line)
        self.console_text.see("end")
        self.home_console.insert("end", line)
        self.home_console.see("end")

    def _drain_queues(self) -> None:
        while True:
            try:
                event = self.ui_events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "log":
                self._append_console(str(event[1]))
            elif kind == "connected":
                protocol, supported = event[1], set(event[2])
                self.supported_pids = supported
                implemented = supported & set(PID_DEFINITIONS)
                self.header_status.configure(text="● CONECTADO", fg=GREEN)
                self.header_protocol.configure(text=f"Protocolo: {protocol}")
                self.side_connection.configure(text="● VEHÍCULO CONECTADO", fg=GREEN)
                self.connection_detail.configure(text=f"Estado: conectado · {protocol} · {len(implemented)} sensores implementados", fg=GREEN)
                self.card_connection.value_label.configure(text="Conectado")  # type: ignore[attr-defined]
                self.card_protocol.value_label.configure(text=str(protocol)[:26])  # type: ignore[attr-defined]
                self._set_status(f"Conectado · ECU anuncia {len(supported)} PID; {len(implemented)} tienen fórmula implementada")
            elif kind == "connect_button":
                self.connect_button.configure(state=event[1])
            elif kind == "error":
                self._set_status(f"Error: {event[2]}")
                messagebox.showerror(event[1], event[2])
            elif kind == "info":
                messagebox.showinfo(event[1], event[2])
            elif kind == "console":
                self._append_console(event[1])
            elif kind == "dtcs":
                found: list[tuple[str, str]] = event[1]
                rows: list[tuple[DTCRecord, str]] = []
                for code, status in found:
                    records = self.database.lookup(code)
                    if records:
                        rows.extend((record, status) for record in records)
                    else:
                        rows.append((DTCRecord(code, "Descripción no disponible", "No identificado", True, ""), status))
                self._populate_dtc_tree(rows)
                self._set_status(f"Escaneo finalizado: {len(found)} códigos únicos")

        while True:
            try:
                packet = self.data_events.get_nowait()
            except queue.Empty:
                break
            timestamp = float(packet.get("timestamp", time.time()))
            values = packet.get("values", {})
            self.latest_values.update(values)
            self.fuel_source = packet.get("fuel_source", "No disponible")
            self.fuel_source_label.configure(text=f"Flujómetro: {self.fuel_source}")
            for pid, value in values.items():
                self.history[pid].append((timestamp, float(value)))
                self.min_values[pid] = min(self.min_values.get(pid, float(value)), float(value))
                self.max_values[pid] = max(self.max_values.get(pid, float(value)), float(value))
                if pid in self.live_items:
                    name, unit = PID_DEFINITIONS[pid]
                    self.live_tree.item(self.live_items[pid], values=(
                        name, f"{value:.2f}", unit, f"{self.min_values[pid]:.2f}", f"{self.max_values[pid]:.2f}", f"01{pid:02X}",
                    ))
                if pid in self.home_items:
                    name, unit = PID_DEFINITIONS[pid]
                    self.home_live.item(self.home_items[pid], values=(name, f"{value:.2f}", unit, f"01{pid:02X}"))
            self.gauge_rpm.set_value(self.latest_values.get(0x0C, 0), 0x0C in values)
            self.gauge_speed.set_value(self.latest_values.get(0x0D, 0), 0x0D in values)
            self.gauge_temp.set_value(self.latest_values.get(0x05, 40), 0x05 in values)
            self.gauge_voltage.set_value(self.latest_values.get(0x42, 8), 0x42 in values)
            scope_pid = self.scope_name_to_pid.get(self.scope_var.get(), 0x0C)
            if scope_pid in values:
                self.scope_canvas.add_sample(values[scope_pid])
                self.scope_samples += 1
                self.scope_rate.configure(text=f"{self.scope_samples} muestras")
            for error in packet.get("errors", []):
                self._append_console(f"[PID] {error}")
        self.after(80, self._drain_queues)

    def _on_close(self) -> None:
        self._stop_live(update_status=False)
        self.client.disconnect()
        self.destroy()


def main() -> None:
    try:
        app = PremiumApp()
        app.mainloop()
    except Exception as exc:
        log_dir = Path.home() / "AppData" / "Local" / "Autoguard" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "AUTOGUARD_INICIO_ERROR.log"
        log_file.write_text(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
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
