from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def configure_logging() -> None:
    """Forgó naplófájlt állít be a hibák és feldolgozási lépések követéséhez."""
    Path("logs").mkdir(exist_ok=True)
    handler = RotatingFileHandler("logs/application.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )
    logging.info("Programinditas")


def main() -> int:
    """Elindítja a Térmonitor-thermal grafikus alkalmazást."""
    configure_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
