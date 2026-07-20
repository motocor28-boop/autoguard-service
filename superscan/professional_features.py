from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .config import APP_NAME, AUTHOR, COLORS
from .professional_reporting import generate_professional_pdf_report
from .solutions import SolutionDatabase

SEVERITY_UI = {
    "BAJA": "#199E63",
    "MEDIA": "#D59A00",
    "ALTA": "#E66B00",
    "CRÍTICA": "#C92E2E",
}


def _set_text(widget: tk.Text, text: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("end", text)
    widget.configure(state="disabled")


def _numbered(items: tuple[str, ...]) -> str:
    return "\n\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"• {item}" for item in items)


def _build_solution_page(self) -> None:
    page = self._new_page("Solución guiada")
    self._section_header(
        page,
        "Solución guiada offline",
        f"Procedimientos, causas y validación para {self.solution_db.count():,} códigos DTC".replace(",", "."),
    )

    search = tk.Frame(page, bg=COLORS["surface_alt"])
    search.pack(fill="x", pady=(0, 10))
    tk.Label(search, text="Código DTC", bg=COLORS["surface_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="left")
    self.solution_code_entry = ttk.Entry(search, width=18)
    self.solution_code_entry.insert(0, "P0171")
    self.solution_code_entry.pack(side="left", padx=8)
    self.solution_code_entry.bind("<Return>", lambda _event: self.show_solution(self.solution_code_entry.get(), navigate=False))
    ttk.Button(search, text="Consultar plan", style="Primary.TButton", command=lambda: self.show_solution(self.solution_code_entry.get(), navigate=False)).pack(side="left")
    ttk.Button(search, text="Usar DTC seleccionado", command=self.open_selected_dtc_solution).pack(side="left", padx=(8, 0))
    self.solution_db_status = tk.Label(
        search,
        text="Base 100 % offline",
        bg=COLORS["surface_alt"],
        fg=COLORS["success"],
        font=("Segoe UI Semibold", 9),
    )
    self.solution_db_status.pack(side="right")

    header = tk.Frame(page, bg=COLORS["nav"], height=82)
    header.pack(fill="x")
    header.pack_propagate(False)
    title_area = tk.Frame(header, bg=COLORS["nav"])
    title_area.pack(side="left", fill="both", expand=True, padx=18, pady=10)
    self.solution_title = tk.Label(title_area, text="P0171 · Sistema de combustible demasiado pobre", bg=COLORS["nav"], fg="white", font=("Segoe UI Semibold", 16), anchor="w")
    self.solution_title.pack(fill="x")
    self.solution_system = tk.Label(title_area, text="Tren motriz · Procedimiento técnico offline", bg=COLORS["nav"], fg="#A9BED2", font=("Segoe UI", 9), anchor="w")
    self.solution_system.pack(fill="x", pady=(4, 0))
    self.solution_severity = tk.Label(header, text="ALTA", bg=SEVERITY_UI["ALTA"], fg="white", font=("Segoe UI Black", 12), padx=18, pady=8)
    self.solution_severity.pack(side="right", padx=18)

    body = tk.Frame(page, bg=COLORS["surface_alt"])
    body.pack(fill="both", expand=True, pady=(12, 0))
    body.columnconfigure(0, weight=2)
    body.columnconfigure(1, weight=5)
    body.rowconfigure(0, weight=1)

    visual_card = self._card(body, padding=12)
    visual_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
    tk.Label(visual_card.inner, text="SISTEMA RELACIONADO", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
    self.solution_canvas = tk.Canvas(visual_card.inner, bg=COLORS["nav"], height=245, highlightthickness=0)
    self.solution_canvas.pack(fill="x", pady=(8, 10))
    self.solution_canvas.bind("<Configure>", lambda _event: self._draw_solution_illustration())
    self.solution_notes = tk.Text(visual_card.inner, height=10, wrap="word", bg=COLORS["surface_alt"], fg=COLORS["text"], relief="flat", font=("Segoe UI", 9), padx=10, pady=10)
    self.solution_notes.pack(fill="both", expand=True)
    self.solution_notes.configure(state="disabled")

    details_card = self._card(body, padding=8)
    details_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
    notebook = ttk.Notebook(details_card.inner)
    notebook.pack(fill="both", expand=True)
    self.solution_notebook = notebook

    tabs: dict[str, tk.Text] = {}
    for title in ("Resumen", "Causas", "Plan de acción", "Validación"):
        tab = tk.Frame(notebook, bg="white")
        notebook.add(tab, text=title)
        text = tk.Text(tab, wrap="word", bg="white", fg=COLORS["text"], relief="flat", font=("Segoe UI", 10), padx=15, pady=15, spacing1=2, spacing3=5)
        text.pack(fill="both", expand=True)
        text.configure(state="disabled")
        tabs[title] = text
    self.solution_texts = tabs
    self.solution_code_current = "P0171"
    self.show_solution("P0171", navigate=False)


def _draw_solution_illustration(self) -> None:
    if not hasattr(self, "solution_canvas"):
        return
    canvas = self.solution_canvas
    canvas.delete("all")
    width = max(canvas.winfo_width(), 260)
    height = max(canvas.winfo_height(), 220)
    cx, cy = width / 2, height / 2
    code = getattr(self, "solution_code_current", "P0171")
    family = code[:1]
    orange = COLORS["accent"]
    blue = "#38A7F2"
    pale = "#C7D8E7"

    canvas.create_rectangle(0, 0, width, height, fill=COLORS["nav"], outline="")
    for x in range(18, int(width), 34):
        canvas.create_line(x, 0, x, height, fill="#0D2943", width=1)
    for y in range(18, int(height), 34):
        canvas.create_line(0, y, width, y, fill="#0D2943", width=1)

    if family == "P":
        canvas.create_rectangle(cx - 82, cy - 52, cx + 72, cy + 52, outline=orange, width=4)
        canvas.create_rectangle(cx - 55, cy - 78, cx + 25, cy - 52, outline=orange, width=4)
        canvas.create_oval(cx - 58, cy - 25, cx - 12, cy + 21, outline=blue, width=4)
        canvas.create_oval(cx + 18, cy - 25, cx + 64, cy + 21, outline=blue, width=4)
        canvas.create_line(cx - 35, cy + 22, cx - 35, cy + 58, fill=pale, width=4)
        canvas.create_line(cx + 41, cy + 22, cx + 41, cy + 58, fill=pale, width=4)
        canvas.create_text(cx, cy + 87, text="MOTOR / COMBUSTIBLE / EMISIONES", fill="white", font=("Segoe UI Semibold", 10))
    elif family == "C":
        canvas.create_oval(cx - 78, cy - 78, cx + 78, cy + 78, outline=orange, width=5)
        canvas.create_oval(cx - 50, cy - 50, cx + 50, cy + 50, outline=blue, width=4)
        canvas.create_oval(cx - 15, cy - 15, cx + 15, cy + 15, fill=pale, outline="")
        canvas.create_arc(cx - 64, cy - 64, cx + 64, cy + 64, start=300, extent=110, style="arc", outline="white", width=12)
        canvas.create_text(cx, cy + 102, text="CHASIS / ABS / ESTABILIDAD", fill="white", font=("Segoe UI Semibold", 10))
    elif family == "B":
        canvas.create_line(cx - 95, cy + 42, cx - 62, cy - 42, cx + 45, cy - 62, cx + 92, cy + 20, cx + 70, cy + 48, cx - 95, cy + 42, fill=orange, width=5, smooth=True)
        canvas.create_oval(cx - 68, cy + 20, cx - 28, cy + 60, outline=blue, width=4)
        canvas.create_oval(cx + 38, cy + 20, cx + 78, cy + 60, outline=blue, width=4)
        canvas.create_oval(cx - 15, cy - 37, cx + 38, cy + 16, outline=pale, width=4)
        canvas.create_text(cx, cy + 91, text="CARROCERÍA / SRS / CONFORT", fill="white", font=("Segoe UI Semibold", 10))
    else:
        nodes = [(cx, cy - 65), (cx - 80, cy), (cx + 80, cy), (cx - 48, cy + 70), (cx + 48, cy + 70)]
        for index, (x, y) in enumerate(nodes):
            for x2, y2 in nodes[index + 1 :]:
                if abs(x - x2) < 135:
                    canvas.create_line(x, y, x2, y2, fill=blue, width=3)
            canvas.create_oval(x - 18, y - 18, x + 18, y + 18, fill=COLORS["nav"], outline=orange, width=4)
        canvas.create_text(cx, cy + 108, text="RED CAN / COMUNICACIÓN", fill="white", font=("Segoe UI Semibold", 10))
    canvas.create_text(18, 18, text=code, anchor="nw", fill=orange, font=("Consolas", 20, "bold"))
    canvas.create_text(width - 18, 20, text="VECTOR HD", anchor="ne", fill="#7791A8", font=("Segoe UI Semibold", 8))


def show_solution(self, code: str, *, navigate: bool = True) -> None:
    normalized = (code or "").strip().upper().replace(" ", "")
    if len(normalized) != 5:
        messagebox.showwarning(APP_NAME, "Ingrese un código DTC válido, por ejemplo P0171.")
        return
    record = self.db.lookup(normalized)
    solution = self.solution_db.lookup(normalized)
    self.solution_code_current = normalized
    self.solution_title.configure(text=f"{normalized} · {record.description}")
    self.solution_system.configure(text=f"{record.system} · {record.scope} · {solution.source_type}")
    self.solution_severity.configure(text=solution.severity, bg=SEVERITY_UI.get(solution.severity, COLORS["primary"]))
    self.solution_code_entry.delete(0, "end")
    self.solution_code_entry.insert(0, normalized)

    summary = (
        f"CÓDIGO: {normalized}\n"
        f"DESCRIPCIÓN: {record.description}\n"
        f"SISTEMA: {record.system}\n"
        f"ALCANCE: {record.scope}\n"
        f"SEVERIDAD: {solution.severity}\n\n"
        "SÍNTOMAS PROBABLES\n"
        f"{_bullets(solution.symptoms)}\n\n"
        "IMPORTANTE\nEl código orienta el diagnóstico, pero no confirma por sí solo la pieza defectuosa."
    )
    causes = "CAUSAS PROBABLES\n\n" + _bullets(solution.causes) + "\n\nHERRAMIENTAS RECOMENDADAS\n\n" + _bullets(solution.tools)
    plan = "PROCESO DE DIAGNÓSTICO PASO A PASO\n\n" + _numbered(solution.steps)
    validation = "VALIDACIÓN DESPUÉS DE LA REPARACIÓN\n\n" + _bullets(solution.validation) + "\n\nNOTAS TÉCNICAS\n\n" + solution.notes
    _set_text(self.solution_texts["Resumen"], summary)
    _set_text(self.solution_texts["Causas"], causes)
    _set_text(self.solution_texts["Plan de acción"], plan)
    _set_text(self.solution_texts["Validación"], validation)
    _set_text(self.solution_notes, f"PRIORIDAD: {solution.severity}\n\n{solution.notes}\n\nLa ilustración es vectorial y se adapta a la resolución de pantalla.")
    self._draw_solution_illustration()
    if navigate:
        self.show_page("Solución guiada")


def open_selected_dtc_solution(self) -> None:
    if hasattr(self, "dtc_tree"):
        selected = self.dtc_tree.selection()
        if selected:
            code = str(self.dtc_tree.item(selected[0], "values")[0])
            self.show_solution(code)
            return
    if self.current_dtcs:
        self.show_solution(self.current_dtcs[0].code)
        return
    self.show_solution(self.solution_code_entry.get() or "P0171")


def _open_tree_solution(self, tree: ttk.Treeview) -> None:
    selected = tree.selection()
    if not selected:
        return
    values = tree.item(selected[0], "values")
    if values:
        self.show_solution(str(values[0]))


def _professional_generate_report(self) -> None:
    self._set_status("Generando informe profesional con gráficos y planes de acción...")
    self.report_status.configure(text="Generando informe profesional...")
    meta = {key: variable.get().strip() for key, variable in self.report_meta_vars.items()}
    include_graphs = bool(self.report_graphs_var.get())
    include_freeze = bool(self.report_freeze_var.get())
    history = {name: list(points) for name, points in self.history.items()} if include_graphs else {}
    freeze_data = dict(getattr(self, "current_freeze", {})) if include_freeze else {}

    def operation() -> Path:
        return generate_professional_pdf_report(
            self.scan_result,
            self.current_dtcs,
            dict(self.current_live),
            history,
            freeze_data,
            self.db,
            self.solution_db,
            vehicle_meta=meta,
        )

    self._run_worker(operation, "report")


def install_professional_features(app_class) -> None:
    if getattr(app_class, "_professional_features_installed", False):
        return

    original_build_shell = app_class._build_shell
    original_build_pages = app_class._build_pages
    original_build_dtc_page = app_class._build_dtc_page
    original_build_database_page = app_class._build_database_page
    original_build_report_page = app_class._build_report_page
    original_populate_dtc_tree = app_class._populate_dtc_tree
    original_on_freeze = app_class._on_freeze

    def build_shell(self) -> None:
        original_build_shell(self)
        name = "Solución guiada"
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
            command=lambda: self.show_page(name),
            cursor="hand2",
        )
        button.pack(fill="x", padx=8, pady=1)
        self.nav_buttons[name] = button

    def build_pages(self) -> None:
        self.solution_db = SolutionDatabase(self.db)
        self.current_freeze: dict[str, tuple[float | None, str]] = {}
        original_build_pages(self)
        self._build_solution_page()

    def build_dtc_page(self) -> None:
        original_build_dtc_page(self)
        self.dtc_tree.bind("<Double-1>", lambda _event: self._open_tree_solution(self.dtc_tree))
        self.dtc_tree.tag_configure("critical", foreground=SEVERITY_UI["CRÍTICA"])
        self.dtc_tree.tag_configure("high", foreground=SEVERITY_UI["ALTA"])
        self.dtc_tree.tag_configure("medium", foreground=SEVERITY_UI["MEDIA"])

    def build_database_page(self) -> None:
        original_build_database_page(self)
        self.db_tree.bind("<Double-1>", lambda _event: self._open_tree_solution(self.db_tree))
        hint = tk.Label(
            self.pages["Base DTC"],
            text="Doble clic sobre un código para abrir causas, proceso paso a paso y validación.",
            bg=COLORS["surface_alt"],
            fg=COLORS["primary"],
            font=("Segoe UI Semibold", 9),
        )
        hint.pack(anchor="w", pady=(6, 0))

    def build_report_page(self) -> None:
        original_build_report_page(self)
        page = self.pages["Informe"]
        meta_card = self._card(page)
        meta_card.pack(fill="x", pady=(12, 0))
        tk.Label(meta_card.inner, text="DATOS DEL INFORME PROFESIONAL", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 11)).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        self.report_meta_vars: dict[str, tk.StringVar] = {
            "technician": tk.StringVar(value=AUTHOR),
            "client": tk.StringVar(),
            "plate": tk.StringVar(),
            "mileage": tk.StringVar(),
        }
        fields = [("Técnico", "technician"), ("Cliente", "client"), ("Patente", "plate"), ("Kilometraje", "mileage")]
        for index, (label_text, key) in enumerate(fields):
            row = 1 + index // 2
            column = (index % 2) * 2
            tk.Label(meta_card.inner, text=label_text, bg="white", fg=COLORS["text"]).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=5)
            entry = ttk.Entry(meta_card.inner, textvariable=self.report_meta_vars[key], width=34)
            entry.grid(row=row, column=column + 1, sticky="ew", padx=(0, 18), pady=5)
        meta_card.inner.columnconfigure(1, weight=1)
        meta_card.inner.columnconfigure(3, weight=1)

        options = self._card(page)
        options.pack(fill="x", pady=(12, 0))
        tk.Label(options.inner, text="CONTENIDO DEL INFORME", bg="white", fg=COLORS["nav"], font=("Segoe UI Semibold", 11)).pack(anchor="w")
        self.report_graphs_var = tk.BooleanVar(value=True)
        self.report_freeze_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options.inner, text="Incluir gráficos HD y valores mínimo/máximo", variable=self.report_graphs_var).pack(anchor="w", pady=(8, 2))
        ttk.Checkbutton(options.inner, text="Incluir Freeze Frame", variable=self.report_freeze_var).pack(anchor="w", pady=2)
        tk.Label(options.inner, text="Los planes de acción, causas, herramientas y checklist se incluyen siempre.", bg="white", fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))

    def populate_dtc_tree(self, dtcs) -> None:
        original_populate_dtc_tree(self, dtcs)
        for item in self.dtc_tree.get_children():
            values = self.dtc_tree.item(item, "values")
            if not values:
                continue
            severity = self.solution_db.lookup(str(values[0])).severity
            tag = "critical" if severity == "CRÍTICA" else "high" if severity == "ALTA" else "medium"
            self.dtc_tree.item(item, tags=(tag,))

    def on_freeze(self, payload: object) -> None:
        self.current_freeze = dict(payload) if isinstance(payload, dict) else {}
        original_on_freeze(self, payload)

    app_class._build_shell = build_shell
    app_class._build_pages = build_pages
    app_class._build_dtc_page = build_dtc_page
    app_class._build_database_page = build_database_page
    app_class._build_report_page = build_report_page
    app_class._populate_dtc_tree = populate_dtc_tree
    app_class._on_freeze = on_freeze
    app_class.generate_report = _professional_generate_report
    app_class._build_solution_page = _build_solution_page
    app_class._draw_solution_illustration = _draw_solution_illustration
    app_class.show_solution = show_solution
    app_class.open_selected_dtc_solution = open_selected_dtc_solution
    app_class._open_tree_solution = _open_tree_solution
    app_class._professional_features_installed = True
