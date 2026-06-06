import sys

from PyQt5.QtWidgets import QApplication

from mapsafe.ui.main_window import MainWindow


def main() -> int:
    """Start the standalone MapSafe desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("MapSafe Python")
    app.setOrganizationName("MapSafe")

    window = MainWindow()
    window.resize(1400, 850)
    window.show()

    return app.exec_()
