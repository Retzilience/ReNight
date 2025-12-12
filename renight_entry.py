# renight_entry.py
# No staged update handshake. Just start the app.

from __future__ import annotations

import sys

import resources_rc  # noqa: F401

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from renight_ui import ReNightWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(":/icons/ReNight.ico"))

    window = ReNightWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
