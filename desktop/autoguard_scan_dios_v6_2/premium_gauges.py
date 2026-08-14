from __future__ import annotations

import math
import tkinter as tk

from premium_app import GREEN, MUTED, ORANGE, ORANGE_LIGHT, PANEL, RED, TEXT, YELLOW


class RealisticGauge(tk.Canvas):
    """High-contrast vector gauge designed for Full HD workshop displays.

    It keeps labels outside the numeric scale and places the digital reading in
    a dedicated display, preventing the overlaps present in the previous dial.
    """

    def __init__(
        self,
        master,
        title: str,
        unit: str,
        minimum: float,
        maximum: float,
        warning: float,
        danger: float,
        size: int = 190,
    ) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            bg=PANEL,
            highlightthickness=0,
            bd=0,
        )
        self.title_text = title
        self.unit = unit
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.warning = float(warning)
        self.danger = float(danger)
        self.value = float(minimum)
        self.signal = False
        self.bind("<Configure>", lambda _event: self.draw())
        self.after_idle(self.draw)

    def set_value(self, value: float, signal: bool = True) -> None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = self.minimum
        self.value = max(self.minimum, min(self.maximum, numeric))
        self.signal = bool(signal)
        self.draw()

    def _ratio(self, value: float) -> float:
        return max(0.0, min(1.0, (value - self.minimum) / max(self.maximum - self.minimum, 0.001)))

    def _angle(self, value: float) -> float:
        # Tk coordinates use positive y down, so calculate with a clockwise arc.
        return math.radians(225.0 - self._ratio(value) * 270.0)

    def _point(self, cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
        return cx + math.cos(angle) * radius, cy - math.sin(angle) * radius

    def _zone_arc(self, cx: float, cy: float, radius: float, start_value: float, end_value: float, color: str) -> None:
        start_ratio = self._ratio(start_value)
        end_ratio = self._ratio(end_value)
        start_deg = -45.0 + start_ratio * 270.0
        extent = max(0.0, (end_ratio - start_ratio) * 270.0)
        self.create_arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            start=start_deg,
            extent=extent,
            style="arc",
            outline=color,
            width=max(5, int(radius * 0.075)),
        )

    def _format_scale(self, value: float) -> str:
        if self.maximum >= 1000:
            return f"{value / 1000:.0f}k"
        if abs(value) >= 100:
            return f"{value:.0f}"
        if abs(value) >= 10:
            return f"{value:.0f}"
        return f"{value:.1f}"

    def _format_value(self) -> str:
        if abs(self.value) >= 1000:
            return f"{self.value:.0f}"
        if abs(self.value) >= 100:
            return f"{self.value:.1f}"
        return f"{self.value:.2f}"

    def draw(self) -> None:
        self.delete("all")
        width = max(155, self.winfo_width())
        height = max(155, self.winfo_height())
        size = min(width, height)
        cx = width / 2.0
        cy = height * 0.47
        radius = size * 0.36

        # Title above the dial, never on top of scale numbers.
        self.create_text(
            cx,
            height * 0.065,
            text=self.title_text,
            fill=TEXT,
            font=("Segoe UI", max(8, int(size * 0.055)), "bold"),
        )

        # Metallic bezel and glass layers.
        rings = (
            (radius + 15, "#AAB2BC", "#D7DCE2", 2),
            (radius + 11, "#4B5560", "#222A33", 3),
            (radius + 7, "#121820", "#7A838E", 2),
            (radius + 2, "#060A0F", "#2B3540", 2),
        )
        for ring_radius, fill, outline, border in rings:
            self.create_oval(
                cx - ring_radius,
                cy - ring_radius,
                cx + ring_radius,
                cy + ring_radius,
                fill=fill,
                outline=outline,
                width=border,
            )
        self.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill="#080D13",
            outline="#0F1720",
            width=2,
        )

        # Warning bands.
        band_radius = radius * 0.88
        self._zone_arc(cx, cy, band_radius, self.minimum, self.warning, GREEN)
        self._zone_arc(cx, cy, band_radius, self.warning, self.danger, YELLOW)
        self._zone_arc(cx, cy, band_radius, self.danger, self.maximum, RED)

        # 41 clean ticks, with only 6 text labels.
        outer = radius * 0.78
        for index in range(41):
            ratio = index / 40.0
            value = self.minimum + ratio * (self.maximum - self.minimum)
            angle = self._angle(value)
            major = index % 8 == 0
            medium = index % 4 == 0
            length = radius * (0.16 if major else 0.105 if medium else 0.06)
            inner = outer - length
            x1, y1 = self._point(cx, cy, inner, angle)
            x2, y2 = self._point(cx, cy, outer, angle)
            tick_color = "#F2F5F8" if major else "#9CA8B4" if medium else "#5C6976"
            self.create_line(x1, y1, x2, y2, fill=tick_color, width=2 if major else 1)
            if major:
                label_radius = inner - radius * 0.12
                lx, ly = self._point(cx, cy, label_radius, angle)
                self.create_text(
                    lx,
                    ly,
                    text=self._format_scale(value),
                    fill="#E7ECF1",
                    font=("Segoe UI", max(7, int(size * 0.043)), "bold"),
                )

        # Needle shadow and needle.
        angle = self._angle(self.value)
        needle_length = radius * 0.69
        nx, ny = self._point(cx, cy, needle_length, angle)
        bx, by = self._point(cx, cy, radius * 0.13, angle + math.pi)
        self.create_line(bx + 2, by + 2, nx + 2, ny + 2, fill="#000000", width=max(4, int(size * 0.025)))
        self.create_line(bx, by, nx, ny, fill=ORANGE, width=max(3, int(size * 0.02)), arrow="last", arrowshape=(9, 11, 4))
        hub = max(7, int(size * 0.045))
        self.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill="#C9D0D7", outline="#020407", width=2)
        self.create_oval(cx - hub * 0.42, cy - hub * 0.42, cx + hub * 0.42, cy + hub * 0.42, fill="#252D36", outline="#818B96")

        # Dedicated digital display below the dial.
        display_y1 = height * 0.73
        display_y2 = height * 0.91
        display_w = width * 0.62
        self.create_rectangle(
            cx - display_w / 2,
            display_y1,
            cx + display_w / 2,
            display_y2,
            fill="#020508",
            outline=ORANGE,
            width=2,
        )
        self.create_text(
            cx,
            (display_y1 + display_y2) / 2 - 2,
            text=self._format_value(),
            fill=ORANGE_LIGHT,
            font=("Consolas", max(14, int(size * 0.105)), "bold"),
        )
        self.create_text(
            cx,
            height * 0.965,
            text=self.unit,
            fill="#DDE3E9",
            font=("Segoe UI", max(8, int(size * 0.05)), "bold"),
        )

        # RX signal indicator remains separate from the scale.
        signal_color = GREEN if self.signal else "#46515D"
        signal_x = cx + radius * 0.62
        signal_y = cy - radius * 0.61
        self.create_oval(signal_x - 5, signal_y - 5, signal_x + 5, signal_y + 5, fill=signal_color, outline="")
        self.create_text(signal_x - 13, signal_y, text="RX", anchor="e", fill=MUTED, font=("Segoe UI", 7, "bold"))
