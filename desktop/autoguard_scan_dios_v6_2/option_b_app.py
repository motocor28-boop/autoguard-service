from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from deep_scan import DeepScanResult, DeepScanner
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
    SIDEBAR,
    TEXT,
    PremiumApp,
)


class OptionBDeepScanApp(PremiumApp):
    """Authorized Option B interface with a read-only deep ECU scan page."""

    def __init__(self) -> None:
        self.deep_events: "queue.Queue[tuple]" = queue.Queue()
        self.deep_result: DeepScanResult | None = None
        self.deep_running = False
        super().__init__()
        self._install_deep_scan_page()
        self.after(100, self._drain_deep_events)

    def _install_deep_scan_page(self) -> None:
        page = self._new_page("Escaneo de sistema")
        self._build_deep_scan(page)
        button = tk.Button(
            self.sidebar,
            text="  ◉   Escaneo de sistema",
            anchor="w",
            relief="flat",
            bg=SIDEBAR,
            fg=TEXT,
            activebackground="#1E2A38",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=10,
            command=lambda: self._show_page("Escaneo de sistema"),
        )
        button.pack(fill="x", padx=8, pady=1, before=self.nav_buttons["Conexión"])
        self.nav_buttons["Escaneo de sistema"] = button

    def _build_deep_scan(self, page: tk.Frame) -> None:
        self._section_title(
            page,
            "Escaneo profundo de sistema",
            "Diagnóstico de solo lectura: ECU, PID, VIN, calibraciones, freeze frame, Mode 06, DTC y UDS",
        )

        toolbar = tk.Frame(page, bg=BG)
        toolbar.pack(fill="x", pady=(0, 9))
        self.deep_start_button = ttk.Button(
            toolbar,
            text="Iniciar escaneo profundo",
            style="Accent.TButton",
            command=self._start_deep_scan,
        )
        self.deep_start_button.pack(side="left", padx=(0, 7))
        self.deep_export_button = ttk.Button(
            toolbar,
            text="Exportar expediente JSON",
            command=self._export_deep_json,
            state="disabled",
        )
        self.deep_export_button.pack(side="left", padx=(0, 7))
        ttk.Button(toolbar, text="Ver DTC y soluciones", command=lambda: self._show_page("DTC y soluciones")).pack(side="left")
        self.deep_elapsed = tk.Label(toolbar, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.deep_elapsed.pack(side="right")

        progress_panel = tk.Frame(page, bg=PANEL, highlightbackground="#334151", highlightthickness=1)
        progress_panel.pack(fill="x", pady=(0, 9))
        self.deep_progress_var = tk.DoubleVar(value=0)
        self.deep_progress = ttk.Progressbar(progress_panel, variable=self.deep_progress_var, maximum=100)
        self.deep_progress.pack(fill="x", padx=12, pady=(11, 5))
        self.deep_progress_text = tk.Label(
            progress_panel,
            text="Listo para iniciar. El proceso no borra códigos ni modifica la ECU.",
            bg=PANEL,
            fg=ORANGE_LIGHT,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )
        self.deep_progress_text.pack(fill="x", padx=12, pady=(0, 10))

        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="x", pady=(0, 9))
        for column in range(5):
            cards.columnconfigure(column, weight=1)
        self.deep_card_modules = self._card(cards, "ECU detectadas", "--", "Respuestas OBD-II y UDS")
        self.deep_card_pids = self._card(cards, "PID publicados", "--", "Bloques 0100 a 01E0")
        self.deep_card_vin = self._card(cards, "VIN", "--", "Mode 09 / UDS F190")
        self.deep_card_dtcs = self._card(cards, "DTC únicos", "--", "Confirmados, pendientes, permanentes y UDS")
        self.deep_card_mode06 = self._card(cards, "Pruebas Mode 06", "--", "Monitores no continuos")
        for index, card in enumerate((
            self.deep_card_modules,
            self.deep_card_pids,
            self.deep_card_vin,
            self.deep_card_dtcs,
            self.deep_card_mode06,
        )):
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 5, 0 if index == 4 else 5))

        notebook = ttk.Notebook(page)
        notebook.pack(fill="both", expand=True)
        summary_tab = tk.Frame(notebook, bg=PANEL)
        module_tab = tk.Frame(notebook, bg=PANEL)
        data_tab = tk.Frame(notebook, bg=PANEL)
        raw_tab = tk.Frame(notebook, bg=PANEL)
        notebook.add(summary_tab, text="Resumen técnico")
        notebook.add(module_tab, text="Módulos y UDS")
        notebook.add(data_tab, text="Sensores y freeze frame")
        notebook.add(raw_tab, text="Datos crudos")

        summary_split = tk.PanedWindow(summary_tab, orient="horizontal", bg=PANEL, sashwidth=6, sashrelief="flat")
        summary_split.pack(fill="both", expand=True, padx=9, pady=9)
        left = tk.Frame(summary_split, bg=PANEL)
        right = tk.Frame(summary_split, bg=PANEL)
        summary_split.add(left, minsize=420)
        summary_split.add(right, minsize=520)

        self.deep_tree = ttk.Treeview(left, columns=("item", "value"), show="headings")
        self.deep_tree.heading("item", text="Elemento")
        self.deep_tree.heading("value", text="Resultado")
        self.deep_tree.column("item", width=225, anchor="w")
        self.deep_tree.column("value", width=310, anchor="w")
        summary_scroll = ttk.Scrollbar(left, orient="vertical", command=self.deep_tree.yview)
        self.deep_tree.configure(yscrollcommand=summary_scroll.set)
        self.deep_tree.pack(side="left", fill="both", expand=True)
        summary_scroll.pack(side="right", fill="y")

        self.deep_summary_text = tk.Text(
            right,
            bg="#070C12",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            wrap="word",
            font=("Segoe UI", 10),
        )
        summary_text_scroll = ttk.Scrollbar(right, orient="vertical", command=self.deep_summary_text.yview)
        self.deep_summary_text.configure(yscrollcommand=summary_text_scroll.set)
        self.deep_summary_text.pack(side="left", fill="both", expand=True)
        summary_text_scroll.pack(side="right", fill="y")
        self.deep_summary_text.insert(
            "end",
            "El escaneo profundo consulta información estándar y datos de identificación UDS de solo lectura.\n\n"
            "No borra DTC, no activa actuadores, no codifica, no reprograma y no cambia parámetros adaptativos.",
        )

        self.deep_modules_tree = ttk.Treeview(
            module_tab,
            columns=("request", "response", "family", "vin", "serial", "software", "dtcs"),
            show="headings",
        )
        for column, title, width in (
            ("request", "Dirección", 90),
            ("response", "Respuesta", 90),
            ("family", "Módulo / familia", 240),
            ("vin", "VIN", 180),
            ("serial", "N.º serie", 150),
            ("software", "Software", 160),
            ("dtcs", "DTC UDS", 220),
        ):
            self.deep_modules_tree.heading(column, text=title)
            self.deep_modules_tree.column(column, width=width, anchor="w")
        modules_scroll = ttk.Scrollbar(module_tab, orient="vertical", command=self.deep_modules_tree.yview)
        self.deep_modules_tree.configure(yscrollcommand=modules_scroll.set)
        self.deep_modules_tree.pack(side="left", fill="both", expand=True, padx=(9, 0), pady=9)
        modules_scroll.pack(side="right", fill="y", padx=(0, 9), pady=9)

        data_split = tk.PanedWindow(data_tab, orient="horizontal", bg=PANEL, sashwidth=6, sashrelief="flat")
        data_split.pack(fill="both", expand=True, padx=9, pady=9)
        live_frame = tk.Frame(data_split, bg=PANEL)
        freeze_frame = tk.Frame(data_split, bg=PANEL)
        data_split.add(live_frame, minsize=520)
        data_split.add(freeze_frame, minsize=520)
        tk.Label(live_frame, text="DATOS ACTUALES DE ECU", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(freeze_frame, text="FREEZE FRAME DISPONIBLE", bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.deep_live_tree = self._parameter_tree(live_frame)
        self.deep_freeze_tree = self._parameter_tree(freeze_frame)

        self.deep_raw_text = tk.Text(
            raw_tab,
            bg="#03070B",
            fg="#75E3A0",
            insertbackground=TEXT,
            relief="flat",
            wrap="none",
            font=("Consolas", 9),
        )
        raw_y = ttk.Scrollbar(raw_tab, orient="vertical", command=self.deep_raw_text.yview)
        raw_x = ttk.Scrollbar(raw_tab, orient="horizontal", command=self.deep_raw_text.xview)
        self.deep_raw_text.configure(yscrollcommand=raw_y.set, xscrollcommand=raw_x.set)
        self.deep_raw_text.pack(side="left", fill="both", expand=True, padx=(9, 0), pady=(9, 0))
        raw_y.pack(side="right", fill="y", padx=(0, 9), pady=(9, 0))
        raw_x.pack(side="bottom", fill="x", padx=9, pady=(0, 9))

    def _parameter_tree(self, parent: tk.Widget) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=("pid", "name", "value", "unit"), show="headings")
        for column, title, width in (
            ("pid", "PID", 80), ("name", "Parámetro", 280),
            ("value", "Valor", 110), ("unit", "Unidad", 80),
        ):
            tree.heading(column, text=title)
            tree.column(column, width=width, anchor="w")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    def _start_deep_scan(self) -> None:
        if self.deep_running:
            return
        if not self.client.connected:
            messagebox.showwarning(
                "Escaneo profundo",
                "Conecte primero el adaptador al vehículo o utilice el simulador.",
            )
            self._show_page("Conexión")
            return
        self.deep_running = True
        self.deep_result = None
        self.deep_start_button.configure(state="disabled")
        self.deep_export_button.configure(state="disabled")
        self.deep_progress_var.set(0)
        self.deep_progress_text.configure(text="Preparando escaneo profundo...", fg=ORANGE_LIGHT)
        self.deep_elapsed.configure(text="")
        self._clear_deep_views()
        started = time.monotonic()

        def progress(value: int, message: str) -> None:
            self.deep_events.put(("progress", value, message, time.monotonic() - started))

        def task() -> None:
            try:
                result = DeepScanner(self.client, progress=progress).run()
                self.deep_events.put(("result", result, time.monotonic() - started))
            except Exception as exc:
                self.deep_events.put(("error", str(exc), time.monotonic() - started))

        threading.Thread(target=task, daemon=True).start()

    def _clear_deep_views(self) -> None:
        for tree in (self.deep_tree, self.deep_modules_tree, self.deep_live_tree, self.deep_freeze_tree):
            for item in tree.get_children():
                tree.delete(item)
        self.deep_summary_text.delete("1.0", "end")
        self.deep_raw_text.delete("1.0", "end")
        for card in (
            self.deep_card_modules,
            self.deep_card_pids,
            self.deep_card_vin,
            self.deep_card_dtcs,
            self.deep_card_mode06,
        ):
            card.value_label.configure(text="--")  # type: ignore[attr-defined]

    def _drain_deep_events(self) -> None:
        while True:
            try:
                event = self.deep_events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "progress":
                self.deep_progress_var.set(event[1])
                self.deep_progress_text.configure(text=event[2], fg=ORANGE_LIGHT)
                self.deep_elapsed.configure(text=f"{event[3]:.1f} s")
                self._set_status(event[2])
            elif kind == "result":
                self.deep_running = False
                self.deep_result = event[1]
                self.deep_start_button.configure(state="normal")
                self.deep_export_button.configure(state="normal")
                self.deep_progress_var.set(100)
                self.deep_progress_text.configure(text="Escaneo profundo finalizado correctamente", fg=GREEN)
                self.deep_elapsed.configure(text=f"{event[2]:.1f} s")
                self._populate_deep_result(event[1])
                self._set_status("Escaneo profundo finalizado")
            elif kind == "error":
                self.deep_running = False
                self.deep_start_button.configure(state="normal")
                self.deep_progress_text.configure(text=f"Error: {event[1]}", fg="#E5484D")
                self.deep_elapsed.configure(text=f"{event[2]:.1f} s")
                messagebox.showerror("Escaneo profundo", event[1])
        self.after(100, self._drain_deep_events)

    def _populate_deep_result(self, result: DeepScanResult) -> None:
        all_dtcs = set()
        for codes in result.dtcs.values():
            all_dtcs.update(codes)
        for module in result.modules:
            all_dtcs.update(module.uds_dtcs)
        vin = result.vehicle_information.get("VIN", "")
        if not vin:
            for module in result.modules:
                if module.vin:
                    vin = module.vin
                    break
        self.deep_card_modules.value_label.configure(text=str(len(result.modules)))  # type: ignore[attr-defined]
        self.deep_card_pids.value_label.configure(text=str(len(result.supported_pids)))  # type: ignore[attr-defined]
        self.deep_card_vin.value_label.configure(text=(vin[:17] if vin else "No publicado"))  # type: ignore[attr-defined]
        self.deep_card_dtcs.value_label.configure(text=str(len(all_dtcs)))  # type: ignore[attr-defined]
        self.deep_card_mode06.value_label.configure(text=str(len(result.mode06_tests)))  # type: ignore[attr-defined]

        rows: list[tuple[str, object]] = [
            ("Protocolo", result.protocol),
            ("Duración", f"{result.finished_at - result.started_at:.2f} s"),
            ("ECU/módulos detectados", len(result.modules)),
            ("PID publicados", len(result.supported_pids)),
            ("PID con fórmula y lectura", len(result.live_values)),
            ("Parámetros freeze frame", len(result.freeze_frame)),
            ("Pruebas Mode 06 crudas", len(result.mode06_tests)),
            ("MIL encendida", result.readiness.get("mil_encendida", "No informado")),
            ("DTC confirmados según PID 0101", result.readiness.get("cantidad_dtc_confirmados", "No informado")),
        ]
        for label, value in result.adapter.items():
            rows.append((f"Adaptador · {label}", value))
        for label, value in result.vehicle_information.items():
            rows.append((label, value))
        for status, codes in result.dtcs.items():
            rows.append((f"DTC {status}", ", ".join(codes) if codes else "Sin códigos"))
        for label, value in rows:
            self.deep_tree.insert("", "end", values=(label, str(value)))

        self.deep_summary_text.delete("1.0", "end")
        self.deep_summary_text.tag_configure("title", foreground=ORANGE, font=("Segoe UI", 13, "bold"))
        self.deep_summary_text.tag_configure("heading", foreground=ORANGE_LIGHT, font=("Segoe UI", 10, "bold"))
        self.deep_summary_text.tag_configure("warning", foreground="#F5C451", font=("Segoe UI", 9, "bold"))
        self.deep_summary_text.insert("end", "RESULTADO DEL ESCANEO PROFUNDO\n", "title")
        self.deep_summary_text.insert(
            "end",
            f"\nProtocolo: {result.protocol}\n"
            f"ECU detectadas: {len(result.modules)}\n"
            f"PID publicados por la ECU: {len(result.supported_pids)}\n"
            f"Datos estándar leídos: {len(result.live_values)}\n"
            f"Freeze frame recuperado: {len(result.freeze_frame)} parámetros\n",
        )
        self.deep_summary_text.insert("end", "\nMONITORES DE PREPARACIÓN\n", "heading")
        self.deep_summary_text.insert("end", json.dumps(result.readiness, ensure_ascii=False, indent=2))
        self.deep_summary_text.insert("end", "\n\nADVERTENCIAS Y ALCANCE\n", "heading")
        for warning in result.warnings:
            self.deep_summary_text.insert("end", f"• {warning}\n", "warning")

        for module in result.modules:
            self.deep_modules_tree.insert(
                "",
                "end",
                values=(
                    module.request_header,
                    module.response_header or "--",
                    module.family,
                    module.vin or "--",
                    module.serial_number or "--",
                    module.software_number or "--",
                    ", ".join(module.uds_dtcs) if module.uds_dtcs else "--",
                ),
            )

        for pid, item in result.live_values.items():
            self.deep_live_tree.insert("", "end", values=(pid, item["name"], f"{float(item['value']):.3f}", item["unit"]))
        for pid, item in result.freeze_frame.items():
            self.deep_freeze_tree.insert("", "end", values=(pid, item["name"], f"{float(item['value']):.3f}", item["unit"]))

        self.deep_raw_text.delete("1.0", "end")
        for key, response in result.raw_responses.items():
            self.deep_raw_text.insert("end", f"===== {key} =====\n{response.strip()}\n\n")

    def _export_deep_json(self) -> None:
        if self.deep_result is None:
            messagebox.showinfo("Exportar", "Primero ejecute un escaneo profundo.")
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        target = filedialog.asksaveasfilename(
            title="Guardar expediente técnico de escaneo",
            defaultextension=".json",
            filetypes=[("Expediente JSON", "*.json")],
            initialfile=f"AUTOGUARD_ESCANEO_PROFUNDO_{stamp}.json",
        )
        if not target:
            return
        path = self.deep_result.save_json(Path(target))
        self._set_status(f"Expediente de escaneo guardado: {path}")
        messagebox.showinfo("Exportación completada", f"Expediente guardado en:\n{path}")


def main() -> None:
    try:
        app = OptionBDeepScanApp()
        app.mainloop()
    except Exception as exc:
        log_dir = Path.home() / "AppData" / "Local" / "Autoguard" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "AUTOGUARD_OPTION_B_INICIO_ERROR.log"
        log_file.write_text(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "AUTOGUARD SCAN DIOS",
                f"No fue posible iniciar la edición B.\n\n{exc}\n\nRegistro: {log_file}",
            )
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
