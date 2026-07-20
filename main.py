from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path

from superscan.logging_config import configure_logging, install_exception_hook


def runtime_self_test() -> int:
    """Valida en el ejecutable compilado las dependencias y módulos críticos."""
    import numpy as np
    import matplotlib
    from matplotlib.figure import Figure
    from reportlab.pdfgen.canvas import Canvas

    from superscan.dtc_database import DTCDatabase, TOTAL_DTC_RECORDS
    from superscan.solutions import SolutionDatabase

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

    dtc_db = DTCDatabase()
    solution_db = SolutionDatabase(dtc_db)
    if dtc_db.count() != TOTAL_DTC_RECORDS or solution_db.count() != TOTAL_DTC_RECORDS:
        raise RuntimeError("Las bases offline DTC y soluciones no están completas")
    if len(solution_db.lookup("P0171").steps) < 8:
        raise RuntimeError("El plan de acción detallado P0171 está incompleto")

    marker = Path(os.environ.get("SUPERSCAN_SELFTEST_MARKER", "SuperScan_runtime_selftest.txt"))
    marker.write_text(
        "OK\n"
        f"NumPy={np.__version__}\n"
        f"Matplotlib={matplotlib.__version__}\n"
        f"DTC={TOTAL_DTC_RECORDS}\n"
        f"Soluciones={solution_db.count()}\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return runtime_self_test()

    from superscan.hd_graphs import install_hd_graphs
    from superscan.professional_features import install_professional_features
    from superscan.ui import SuperScanApp

    install_professional_features(SuperScanApp)
    install_hd_graphs(SuperScanApp)
    logger = configure_logging()
    install_exception_hook(logger)
    app = SuperScanApp(logger)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
