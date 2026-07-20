from __future__ import annotations

import sys
import traceback
from pathlib import Path


def main() -> None:
    from superscan.logging_config import configure_logging, install_exception_hook
    from superscan.professional_ui import ProfessionalSuperScanApp

    logger = configure_logging()
    install_exception_hook(logger)
    app = ProfessionalSuperScanApp(logger)
    app.mainloop()


def selftest() -> int:
    """Prueba de arranque del ejecutable compilado sin abrir la interfaz."""
    import matplotlib
    import numpy
    import reportlab

    from superscan.dtc_database import DTCDatabase, TOTAL_DTC_RECORDS
    from superscan.solution_engine import OfflineSolutionDatabase

    dtc = DTCDatabase()
    solutions = OfflineSolutionDatabase()
    assert dtc.count() == TOTAL_DTC_RECORDS == 12_133
    assert solutions.count() == TOTAL_DTC_RECORDS
    assert solutions.lookup("P0171").steps
    assert numpy.__version__
    assert matplotlib.__version__
    assert reportlab.Version
    return 0


def run_selftest_with_diagnostics() -> int:
    """Ejecuta la autoprueba y registra cualquier error aunque no exista consola."""
    diagnostic = Path.cwd() / "SUPERSCAN_SELFTEST_ERROR.txt"
    try:
        diagnostic.unlink(missing_ok=True)
        return selftest()
    except BaseException:
        diagnostic.write_text(traceback.format_exc(), encoding="utf-8")
        return 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(run_selftest_with_diagnostics())
    main()
