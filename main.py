from __future__ import annotations

import sys

from superscan.logging_config import configure_logging, install_exception_hook
from superscan.professional_ui import ProfessionalSuperScanApp


def main() -> None:
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
    print("SUPERSCAN_PROFESSIONAL_SELFTEST_OK")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    main()
