from __future__ import annotations

from superscan.logging_config import configure_logging, install_exception_hook
from superscan.ui import SuperScanApp


def main() -> None:
    logger = configure_logging()
    install_exception_hook(logger)
    app = SuperScanApp(logger)
    app.mainloop()


if __name__ == "__main__":
    main()
