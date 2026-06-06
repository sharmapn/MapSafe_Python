"""Right-side map panel for the MapSafe Python desktop application.

The standalone app keeps the map visible at all times.  This module wraps the
map functionality in a reusable QWidget so the main window can focus on workflow
controls while this class focuses only on map rendering.
"""

# Enable postponed evaluation of type annotations.
from __future__ import annotations

# tempfile is used to create a temporary HTML file for the Folium map.
import tempfile

# Path gives safer cross-platform file path handling.
from pathlib import Path

# Optional is used for optional style dictionaries.
from typing import Optional

# Folium creates Leaflet-based interactive web maps as HTML.
import folium

# GeoPandas layers are passed into this widget for map display.
import geopandas as gpd

# QUrl is used to load the local Folium HTML file into QWebEngineView.
from PyQt5.QtCore import QUrl

# QLabel is used as a fallback if PyQtWebEngine is unavailable.  QVBoxLayout and
# QWidget are standard PyQt layout/widget classes.
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

# PyQtWebEngine is sometimes installed separately from PyQt5.  The try/except
# allows the application to start and show a useful message if it is missing.
try:
    # QWebEngineView is an embedded browser widget.  It displays the Folium HTML
    # map inside the desktop application.
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover
    # If PyQtWebEngine is not installed, store None and show a fallback label.
    QWebEngineView = None


class MapView(QWidget):
    """Right-side map panel for the standalone desktop application."""

    def __init__(self, parent=None):
        """Create the map widget and display an initial empty Fiji map.

        Args:
            parent: Optional Qt parent widget.
        """

        # Initialise QWidget base class.
        super().__init__(parent)

        # Store map layers as tuples: (layer name, GeoDataFrame copy, style dict).
        # A copy is stored so later edits to the source object do not unexpectedly
        # change the rendered map.
        self.layers: list[tuple[str, gpd.GeoDataFrame, dict]] = []

        # Folium renders maps to HTML.  We save that HTML to the operating system
        # temp folder and load it in the embedded browser.
        self.html_path = Path(tempfile.gettempdir()) / "mapsafe_python_map.html"

        # Create a layout with no margins so the map fills the entire right panel.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # If PyQtWebEngine is missing, show installation instructions rather than
        # crashing the whole app.
        if QWebEngineView is None:
            self.web_view = QLabel(
                "PyQtWebEngine is not installed.\n\n"
                "Install it with:\n"
                "pip install PyQtWebEngine\n\n"
                "The right panel is reserved for the map."
            )

            # Allow the fallback text to wrap inside the panel.
            self.web_view.setWordWrap(True)
        else:
            # Use the embedded browser widget when PyQtWebEngine is available.
            self.web_view = QWebEngineView()

        # Add either the embedded browser or fallback label to the layout.
        layout.addWidget(self.web_view)

        # Show a neutral starting map before the user loads any data.
        self.show_empty_map()

    def show_empty_map(self) -> None:
        """Display a neutral starting map centred on Fiji."""

        # Create a Folium map centred roughly on Fiji.  This is useful for the
        # MapSafe context and gives the user an immediate visual map area.
        fmap = folium.Map(location=[-17.7134, 178.0650], zoom_start=7, tiles="OpenStreetMap")

        # Save the generated map to HTML and load it in the map panel.
        self._save_and_load(fmap)

    def set_layer(self, name: str, gdf: gpd.GeoDataFrame, style: Optional[dict] = None) -> None:
        """Replace all displayed layers with one layer.

        Args:
            name: Layer name shown in the map layer control.
            gdf: GeoDataFrame to display.
            style: Optional Folium style dictionary.
        """

        # Clear all existing layers so the new layer becomes the only map layer.
        self.layers = []

        # Add the new layer without rendering immediately; rendering is triggered
        # explicitly on the next line.
        self.add_layer(name, gdf, style=style, render=False)

        # Render the updated layer list.
        self.render()

    def add_layer(
        self,
        name: str,
        gdf: gpd.GeoDataFrame,
        style: Optional[dict] = None,
        render: bool = True,
    ) -> None:
        """Add a layer to the map.

        Args:
            name: Layer name shown in the map layer control.
            gdf: GeoDataFrame to add.
            style: Optional Folium style dictionary.
            render: Whether to immediately redraw the map.
        """

        # Store a copy of the layer to avoid accidental mutation from outside the
        # map view.
        self.layers.append((name, gdf.copy(), style or {}))

        # Redraw the map immediately unless the caller is batching layer changes.
        if render:
            self.render()

    def render(self) -> None:
        """Render all stored layers in the map panel."""

        # If there are no layers, show the neutral starting map.
        if not self.layers:
            self.show_empty_map()
            return

        # Use the first layer to calculate the map centre.  Reproject to WGS84
        # because Leaflet/Folium expects longitude/latitude coordinates.
        first_wgs84 = self.layers[0][1].to_crs("EPSG:4326")

        # total_bounds returns [minx, miny, maxx, maxy].  In EPSG:4326, x is
        # longitude and y is latitude.
        minx, miny, maxx, maxy = first_wgs84.total_bounds

        # Folium wants location as [latitude, longitude], so the order is y, x.
        centre = [(miny + maxy) / 2.0, (minx + maxx) / 2.0]

        # Create a new Folium map centred on the data.  A fixed zoom is used for
        # simplicity in this first version.
        fmap = folium.Map(location=centre, zoom_start=13, tiles="OpenStreetMap")

        # Add every stored layer to the Folium map.
        for name, layer, style in self.layers:
            # Reproject each layer to WGS84 so it displays correctly in Leaflet.
            wgs84 = layer.to_crs("EPSG:4326")

            # Add the layer as GeoJSON.  Folium can display points, lines, and
            # polygons from GeoJSON data.
            folium.GeoJson(
                # Convert the GeoDataFrame to a GeoJSON string.
                data=wgs84.to_json(),

                # Display name used by Folium's layer control.
                name=name,

                # Use a provided style if one exists; otherwise use a simple
                # default style for line/polygon features.
                style_function=lambda _feature, layer_style=style: layer_style or {
                    "weight": 2,
                    "fillOpacity": 0.25,
                },

                # Marker style for point features.  Folium applies this to point
                # geometries in the GeoJSON layer.
                marker=folium.CircleMarker(radius=4, weight=1, fill=True, fill_opacity=0.8),
            ).add_to(fmap)

        # Add a layer switcher so users can toggle original/masked/binned layers.
        folium.LayerControl().add_to(fmap)

        # Save and display the finished map.
        self._save_and_load(fmap)

    def _save_and_load(self, fmap: folium.Map) -> None:
        """Save a Folium map to HTML and load it into the map panel.

        Args:
            fmap: Folium map object to display.
        """

        # Write the Folium-generated HTML file to the temporary path.
        fmap.save(str(self.html_path))

        # If QWebEngineView is available, load the local HTML file into the
        # embedded browser.
        if QWebEngineView is not None:
            self.web_view.load(QUrl.fromLocalFile(str(self.html_path)))

        # If PyQtWebEngine is missing, show the path to the generated HTML so the
        # user can still open it manually in a browser if needed.
        else:
            self.web_view.setText(f"Map HTML written to:\n{self.html_path}")
