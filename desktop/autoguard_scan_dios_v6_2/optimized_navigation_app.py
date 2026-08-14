from __future__ import annotations

import queue
import time
import tkinter as tk
from contextlib import contextmanager
from types import TracebackType
from typing import Any, Callable, Iterator

from core import PID_DEFINITIONS
from navigation_premium_app import NavigationPremiumApp
from premium_app import ORANGE, ORANGE_LIGHT

NAV_VERSION = "6.2.6 PARCHE CONSOLIDADO"
NAV_BUILD = "Inicio en menú · Navegación fluida · Informe maestro · Recuperación automática"

_PAGE_LABELS = {
    "Inicio": "Menú principal y accesos directos",
    "Datos en vivo": "Panel de lecturas principales, relojes y estado de la sesión",
    "Sensores por sistema": "Selección, lectura y ventanas individuales por sensor",
    "Osciloscopio ECU": "Osciloscopio multicanal de telemetría ECU",
    "Escaneo y códigos": "Códigos activos, soluciones offline e historial de borrado",
    "Escaneo profundo": "Escaneo profundo OBD-II y UDS de solo lectura",
    "Pruebas funcionales": "Pruebas guiadas para confirmar el diagnóstico",
    "Información del vehículo": "Identificación del vehículo, módulos y ECU",
    "Informe Premium": "Informe PDF maestro con subinforme técnico por DTC",
    "Historial": "Historial de sesiones, capturas y operaciones",
    "Conexión": "Conexión ELM327, puertos COM, WiFi y simulador",
    "Ayuda": "Ayuda técnica y alcance de la aplicación",
}


class OptimizedNavigationApp(NavigationPremiumApp):
    """Capa consolidada con inicio limpio, renderizado selectivo y ciclo Tk seguro."""

    def __init__(self) -> None:
        # Estos atributos deben existir antes de que PremiumApp programe el primer
        # callback after(). Así la llamada inicial también queda bajo control.
        self._closing = False
        self._drain_after_id: str | None = None
        self._drain_running = False
        self._startup_complete = False
        self._active_page_name: str | None = None
        self._previous_page_name: str | None = None
        self._page_switching = False
        self._last_scope_redraw = 0.0
        self._last_gauge_redraw: dict[int, float] = {}
        super().__init__()
        self.title(f"AUTOGUARD SCAN DIOS v{NAV_VERSION}")
        self._startup_complete = True
        self._show_page("Inicio")
        self.update_idletasks()
        try:
            self.deiconify()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Ciclo after() protegido
    # ------------------------------------------------------------------
    @staticmethod
    def _is_drain_callback(func: Callable[..., Any]) -> bool:
        return getattr(func, "__name__", "") == "_drain_queues"

    def after(self, ms: int, func: Callable[..., Any] | None = None, *args: Any) -> str:
        """Intercepta solamente el temporizador principal y evita duplicados."""
        if func is not None and self._is_drain_callback(func):
            return self._schedule_drain(ms)
        if getattr(self, "_closing", False):
            return ""
        return super().after(ms, func, *args)

    def _schedule_drain(self, ms: int = 80) -> str:
        if getattr(self, "_closing", False):
            return ""

        existing = getattr(self, "_drain_after_id", None)
        if existing:
            try:
                super().after_cancel(existing)
            except tk.TclError:
                pass
            self._drain_after_id = None

        def run_once() -> None:
            self._drain_after_id = None
            if self._closing:
                return
            if self._drain_running:
                self._schedule_drain(ms)
                return
            self._drain_running = True
            try:
                self._drain_queues()
            except tk.TclError as exc:
                # Un callback tardío durante el cierre no debe convertir un cierre
                # normal en un fallo de inicio.
                if self._closing or "invalid command name" in str(exc).casefold():
                    return
                raise
            finally:
                self._drain_running = False

        self._drain_after_id = super().after(max(20, int(ms)), run_once)
        return self._drain_after_id

    def _cancel_drain_loop(self) -> None:
        callback_id = getattr(self, "_drain_after_id", None)
        self._drain_after_id = None
        if callback_id:
            try:
                super().after_cancel(callback_id)
            except tk.TclError:
                pass

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._cancel_drain_loop()
        try:
            super()._on_close()
        except tk.TclError as exc:
            if "invalid command name" not in str(exc).casefold():
                raise

    def destroy(self) -> None:
        self._closing = True
        self._cancel_drain_loop()
        try:
            super().destroy()
        except tk.TclError as exc:
            if "invalid command name" not in str(exc).casefold():
                raise

    def report_callback_exception(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        if isinstance(exc_value, tk.TclError):
            message = str(exc_value).casefold()
            if self._closing or "invalid command name" in message:
                return
        super().report_callback_exception(exc_type, exc_value, exc_traceback)

    # ------------------------------------------------------------------
    # Construcción e intercambio de páginas
    # ------------------------------------------------------------------
    def _build_pages(self) -> None:
        # La ventana permanece oculta mientras se construyen las páginas. De esta
        # forma los relojes nunca aparecen antes que el menú principal.
        try:
            self.withdraw()
        except tk.TclError:
            pass
        super()._build_pages()

    def _show_page(self, name: str) -> None:
        pages = getattr(self, "pages", None)
        if not pages or self._closing:
            return
        if not self._startup_complete and "Inicio" in pages:
            name = "Inicio"
        if name not in pages or self._page_switching:
            return
        if self._active_page_name == name:
            return

        self._page_switching = True
        try:
            previous = self._active_page_name
            pages[name].tkraise()
            self._previous_page_name = previous
            self._active_page_name = name

            buttons = getattr(self, "nav_buttons", {})
            if previous in buttons:
                buttons[previous].configure(
                    bg="#060A0F",
                    fg="#D5DCE4",
                    highlightbackground="#060A0F",
                )
            if name in buttons:
                buttons[name].configure(
                    bg="#3A210C",
                    fg=ORANGE_LIGHT,
                    highlightbackground=ORANGE,
                )

            section = getattr(self, "current_section_var", None)
            if section is not None:
                section.set(_PAGE_LABELS.get(name, name))

            # El refresco de la página activa se difiere al ciclo ocioso de Tk.
            # No se fuerza update() durante el clic, por lo que la navegación no
            # queda bloqueada por gráficos o tablas ocultas.
            self.after_idle(self._refresh_active_page)
        finally:
            self._page_switching = False

    def _refresh_active_page(self) -> None:
        if self._closing:
            return
        active = self._active_page_name
        if active == "Datos en vivo":
            for gauge_name in (
                "live_gauge_rpm",
                "live_gauge_speed",
                "live_gauge_voltage",
                "live_gauge_coolant",
                "live_gauge_map",
                "live_gauge_oil",
            ):
                gauge = getattr(self, gauge_name, None)
                if gauge is not None:
                    try:
                        gauge.draw()
                    except tk.TclError:
                        pass
            self._refresh_dashboard_from_latest()
        elif active == "Sensores por sistema":
            self._refresh_sensor_table_from_latest()
        elif active == "Osciloscopio ECU":
            canvas = getattr(self, "scope_page_canvas", None)
            if canvas is not None:
                try:
                    canvas.redraw()
                except tk.TclError:
                    pass

    def _refresh_dashboard_from_latest(self) -> None:
        tree = getattr(self, "dashboard_tree", None)
        items = getattr(self, "dashboard_items", {})
        if tree is None or self._closing:
            return
        for pid, item in items.items():
            name, unit = PID_DEFINITIONS.get(pid, (f"PID 01{pid:02X}", ""))
            value = self.latest_values.get(pid)
            formatted = "--" if value is None else self._format_live_value(value)
            tree.item(item, values=(name, formatted, unit, f"01{pid:02X}"))

    def _refresh_sensor_table_from_latest(self) -> None:
        tree = getattr(self, "live_tree", None)
        items = getattr(self, "live_items", {})
        if tree is None or self._closing:
            return
        for pid, item in items.items():
            name, unit = PID_DEFINITIONS.get(pid, (f"PID 01{pid:02X}", ""))
            value = self.latest_values.get(pid)
            minimum = self.min_values.get(pid)
            maximum = self.max_values.get(pid)
            tree.item(
                item,
                values=(
                    name,
                    "--" if value is None else self._format_live_value(value),
                    unit,
                    "--" if minimum is None else self._format_live_value(minimum),
                    "--" if maximum is None else self._format_live_value(maximum),
                    f"01{pid:02X}",
                ),
            )

    @staticmethod
    def _format_live_value(value: float) -> str:
        absolute = abs(float(value))
        if absolute >= 1000:
            return f"{value:.0f}"
        if absolute >= 100:
            return f"{value:.1f}"
        return f"{value:.2f}"

    def _coalesce_live_packets(self) -> None:
        data_events = getattr(self, "data_events", None)
        if data_events is None:
            return
        packets: list[dict[str, Any]] = []
        while True:
            try:
                packets.append(data_events.get_nowait())
            except queue.Empty:
                break
        if not packets:
            return
        if len(packets) == 1:
            data_events.put(packets[0])
            return

        merged: dict[str, Any] = {
            "timestamp": packets[-1].get("timestamp", time.time()),
            "values": {},
            "fuel_source": packets[-1].get("fuel_source", "No disponible"),
            "errors": [],
        }
        for packet in packets:
            merged["values"].update(packet.get("values", {}))
            merged["errors"].extend(packet.get("errors", []))
            if packet.get("fuel_source"):
                merged["fuel_source"] = packet["fuel_source"]
        data_events.put(merged)

    @contextmanager
    def _render_policy(self) -> Iterator[None]:
        saved: list[tuple[Any, str, Callable[..., Any]]] = []
        active = self._active_page_name or "Inicio"

        def replace(obj: Any, name: str, replacement: Callable[..., Any]) -> None:
            if obj is None or not hasattr(obj, name):
                return
            original = getattr(obj, name)
            saved.append((obj, name, original))
            setattr(obj, name, replacement)

        # El osciloscopio dedicado se redibuja una sola vez por ciclo y únicamente
        # cuando su página está visible. set_pids conserva la selección aunque la
        # página permanezca oculta.
        scope = getattr(self, "scope_page_canvas", None)
        if scope is not None:
            original_redraw = scope.redraw

            def limited_scope_redraw(*_args: Any, **_kwargs: Any) -> None:
                if active != "Osciloscopio ECU" or self._closing:
                    return
                now = time.monotonic()
                if now - self._last_scope_redraw < 0.10:
                    return
                self._last_scope_redraw = now
                original_redraw()

            replace(scope, "redraw", limited_scope_redraw)

        # El osciloscopio heredado conserva las muestras, pero no dibuja una
        # segunda gráfica que no está visible en la navegación final.
        legacy_scope = getattr(self, "scope_canvas", None)
        if legacy_scope is not None and hasattr(legacy_scope, "samples"):
            def add_sample_without_redraw(value: float) -> None:
                legacy_scope.samples.append(float(value))
            replace(legacy_scope, "add_sample", add_sample_without_redraw)

        # Los relojes actualizan su valor interno siempre, pero solo repintan en
        # Datos en vivo y con un límite de diez cuadros por segundo.
        seen_gauges: set[int] = set()
        for gauge_name in (
            "gauge_rpm",
            "gauge_speed",
            "gauge_temp",
            "gauge_voltage",
            "live_gauge_rpm",
            "live_gauge_speed",
            "live_gauge_voltage",
            "live_gauge_coolant",
            "live_gauge_map",
            "live_gauge_oil",
        ):
            gauge = getattr(self, gauge_name, None)
            if gauge is None or id(gauge) in seen_gauges:
                continue
            seen_gauges.add(id(gauge))

            def limited_set_value(value: float, signal: bool = True, target: Any = gauge) -> None:
                try:
                    target.value = max(target.minimum, min(target.maximum, float(value)))
                    target.signal = signal
                    now = time.monotonic()
                    last = self._last_gauge_redraw.get(id(target), 0.0)
                    if active == "Datos en vivo" and now - last >= 0.10 and not self._closing:
                        self._last_gauge_redraw[id(target)] = now
                        target.draw()
                except (tk.TclError, AttributeError):
                    pass

            replace(gauge, "set_value", limited_set_value)

        # Las tablas grandes se actualizan únicamente cuando su página está
        # visible. Al entrar a la página se reconstruyen desde latest_values.
        if active != "Datos en vivo":
            dashboard = getattr(self, "dashboard_tree", None)
            replace(dashboard, "item", lambda *_args, **_kwargs: "")
        if active != "Sensores por sistema":
            live_tree = getattr(self, "live_tree", None)
            replace(live_tree, "item", lambda *_args, **_kwargs: "")
        if active != "Osciloscopio ECU":
            trace_tree = getattr(self, "scope_trace_tree", None)
            replace(trace_tree, "item", lambda *_args, **_kwargs: "")

        try:
            yield
        finally:
            for obj, name, original in reversed(saved):
                try:
                    setattr(obj, name, original)
                except (tk.TclError, AttributeError):
                    pass

    def _drain_queues(self) -> None:
        if self._closing:
            return
        # Se conserva el último valor de cada PID y se evita dibujar repetidamente
        # paquetes acumulados durante una operación pesada.
        self._coalesce_live_packets()
        with self._render_policy():
            super()._drain_queues()


def run_navigation_self_test() -> None:
    app = OptimizedNavigationApp()
    try:
        app.withdraw()
        app.update_idletasks()
        if app._active_page_name != "Inicio":
            raise RuntimeError(f"La aplicación inició en {app._active_page_name!r} y no en el menú")
        started = time.perf_counter()
        for page_name in app.pages:
            app._show_page(page_name)
            app.update_idletasks()
        app._show_page("Inicio")
        app.update_idletasks()
        elapsed = time.perf_counter() - started
        if app._active_page_name != "Inicio":
            raise RuntimeError("No fue posible regresar al menú principal")
        if elapsed > 5.0:
            raise RuntimeError(f"La navegación interna demoró {elapsed:.2f} segundos")
    finally:
        app.destroy()
