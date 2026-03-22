"""Launch the PySide6 control centre UI."""

from __future__ import annotations

import sys

from src.ui.main_window import ControlCentreWindow
from src.ui.qt import QApplication


def main() -> None:
    app = QApplication(sys.argv)
    window = ControlCentreWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
