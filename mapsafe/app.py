"""Application bootstrap for MapSafe Python.

This module contains the startup function for the standalone desktop
application.  The GUI itself is defined in ``mapsafe.ui.main_window``; this file
only creates the Qt application object, creates the main window, and starts the
Qt event loop.
"""

# ``sys.argv`` is passed to QApplication so Qt can read normal command-line
# arguments if needed, for example platform plugin options.
import sys

# QApplication is the required top-level Qt object for every PyQt desktop app.
# It manages the event loop, application-wide settings, and GUI resources.
from PyQt5.QtWidgets import QApplication

# MainWindow contains the actual two-panel MapSafe user interface.
from mapsafe.ui.main_window import MainWindow


def main() -> int:
    """Start the standalone MapSafe desktop application.

    Returns:
        int: The Qt application exit code. Returning this value is useful for
        packaging tools and operating systems because it indicates whether the
        GUI closed normally or exited with an error.
    """

    # Create the single QApplication instance required by PyQt.
    # Only one QApplication should exist in a desktop process.
    app = QApplication(sys.argv)

    # Set a human-readable application name. Qt may use this in window metadata,
    # settings storage, task managers, or desktop integration.
    app.setApplicationName("MapSafe Python")

    # Set the organisation name. This is useful later if persistent settings are
    # stored using QSettings.
    app.setOrganizationName("MapSafe")

    # Create the main application window. The window builds the left control
    # panel and the right map panel in its constructor.
    window = MainWindow()

    # Give the application a comfortable default size. Users can still resize
    # the window after it opens.
    window.resize(1400, 850)

    # Display the main window on screen.
    window.show()

    # Start Qt's event loop. This call blocks until the user closes the app.
    # The returned integer is the application exit code.
    return app.exec_()
