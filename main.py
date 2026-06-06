"""Top-level entry point for the MapSafe Python desktop application.

This file is intentionally very small.  Keeping the entry point small makes the
application easier to package later with tools such as PyInstaller, because the
real application startup logic remains inside the reusable ``mapsafe`` package.
"""

# Import the main application bootstrap function from the internal package.
# The function creates the QApplication, builds the main window, and starts the
# Qt event loop.
from mapsafe.app import main


# Python sets ``__name__`` to ``"__main__"`` only when this file is executed
# directly, for example with: ``python main.py``.
#
# This guard prevents the GUI from starting accidentally if another module imports
# this file during testing, packaging, or documentation generation.
if __name__ == "__main__":
    # Start the MapSafe Python desktop application.
    main()
