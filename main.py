from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path

from superscan.logging_config import configure_logging, install_exception_hook


def runtime_self_test() -> int:
    """Valida en el ejecutable compilado las dependencias nativas críticas."""
    import numpy as np
    import matplotlib
    from matplotlib.figure import Figure
    from reportlab.pdfgen.canvas import Canvas

    from superscan.dtc_database import TOTAL_DTC_RECORDS

    values = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    if float(values.sum()) != 6.0:
        raise RuntimeError("La operación nativa de NumPy no respondió correctamente")

    figure = Figure(figsize=(2, 1))
    axis = figure.subplots()
    axis.plot([0, 1], [0, 1])

    pdf_buffer = BytesIO()
    canvas = Canvas(pdf_buffer)
    canvas.drawString(20, 20, "SuperScan 2.0 runtime self-test")
    canvas.save()
    if not pdf_buffer.getvalue().startswith(b"%PDF"):
        raise RuntimeError("ReportLab no generó un PDF válido")

    if TOTAL_DTC_RECORDS != 12133:
        raise RuntimeError(f"Catálogo DTC inesperado: {TOTAL_DTC_RECORDS}")

    marker = Path(os.environ.get("SUPERSCAN_SELFTEST_MARKER", "SuperScan_runtime_selftest.txt"))
    marker.write_text(
        "OK\n"
        f"NumPy={np.__version__}\n"
        f"Matplotlib={matplotlib.__version__}\n"
        f"DTC={TOTAL_DTC_RECORDS}\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return runtime_self_test()

    from superscan.ui import SuperScanApp

    logger = configure_logging()
    install_exception_hook(logger)
    app = SuperScanApp(logger)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
