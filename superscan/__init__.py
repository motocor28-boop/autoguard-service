"""SuperScan 2.0 Profesional — diagnóstico automotriz AutoGuard."""

from __future__ import annotations

__version__ = "2.1.0"


def _install_professional_report_color_compatibility() -> None:
    """Adapta la paleta del informe a colores hexadecimales de Matplotlib.

    ReportLab y Matplotlib utilizan objetos de color distintos. Esta corrección
    mantiene los colores AutoGuard y evita convertir objetos ReportLab a cadenas
    no válidas para los gráficos PNG incorporados en el PDF.
    """

    from io import BytesIO

    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from . import professional_reporting

    severity_hex = {
        "CRÍTICA": "#E64545",
        "ALTA": "#E55B2D",
        "MEDIA": "#F39C12",
        "BAJA": "#20B66A",
    }

    def donut_image(distribution):
        labels = [name for name, value in distribution.items() if value]
        values = [value for value in distribution.values() if value]
        if not values:
            labels, values = ["Sin DTC"], [1]
            palette = ["#20B66A"]
        else:
            palette = [severity_hex.get(name, "#168DFF") for name in labels]

        figure = Figure(figsize=(3.2, 2.2), dpi=160, facecolor="white")
        axis = figure.add_subplot(111)
        axis.pie(
            values,
            labels=labels,
            colors=palette,
            startangle=90,
            wedgeprops={"width": 0.38, "edgecolor": "white"},
            textprops={"fontsize": 7},
        )
        axis.text(
            0,
            0,
            str(sum(values) if labels != ["Sin DTC"] else 0),
            ha="center",
            va="center",
            fontsize=18,
            fontweight="bold",
        )
        axis.set_title("Distribución de severidad", fontsize=9, fontweight="bold")
        figure.tight_layout()
        buffer = BytesIO()
        FigureCanvasAgg(figure).print_png(buffer)
        buffer.seek(0)
        return buffer

    professional_reporting._donut_image = donut_image


_install_professional_report_color_compatibility()
del _install_professional_report_color_compatibility
