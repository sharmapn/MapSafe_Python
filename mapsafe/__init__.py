"""Standalone MapSafe desktop application package.

The ``mapsafe`` package contains the reusable application code for the
standalone Python version of MapSafe.

Package structure:

- ``mapsafe.core`` contains geoprivacy and file-processing logic.
- ``mapsafe.ui`` contains PyQt user-interface widgets.
- ``mapsafe.app`` contains the GUI bootstrap function.
"""

# Central package version.  Keeping this value here makes it easier to expose the
# application version in the UI, logs, or future packaging metadata.
__version__ = "0.1.0"
