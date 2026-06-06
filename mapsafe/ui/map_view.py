from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import folium
import geopandas as gpd
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover
    QWebEngineView = None


class MapView(QWidget):
    """Right-side map panel for the standalone desktop application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layers: list[tuple[str, gpd.GeoDataFrame, dict]] = []
        self.html_path = Path(tempfile.gettempdir()) / "mapsafe_python_map.html"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if QWebEngineView is None:
            self.web_view = QLabel(
                "PyQtWebEngine is not installed.\n\n"
                "Install it with:\n"
                "pip install PyQtWebEngine\n\n"
                "The right panel is reserved for the map."
            )
            self.web_view.setWordWrap(True)
        else:
            self.web_view = QWebEngineView()

        layout.addWidget(self.web_view)
        self.show_empty_map()

    def show_empty_map(self) -> None:
        """Display a neutral starting map."""
        fmap = folium.Map(location=[-17.7134, 178.0650], zoom_start=7, tiles="OpenStreetMap")
        self._save_and_load(fmap)

    def set_layer(self, name: str, gdf: gpd.GeoDataFrame, style: Optional[dict] = None) -> None:
        """Replace all displayed layers with one layer."""
        self.layers = []
        self.add_layer(name, gdf, style=style, render=False)
        self.render()

    def add_layer(
        self,
        name: str,
        gdf: gpd.GeoDataFrame,
        style: Optional[dict] = None,
        render: bool = True,
    ) -> None:
        """Add a layer to the map."""
        self.layers.append((name, gdf.copy(), style or {}))
        if render:
            self.render()

    def render(self) -> None:
        """Render all layers in the map panel."""
        if not self.layers:
            self.show_empty_map()
            return

        first_wgs84 = self.layers[0][1].to_crs("EPSG:4326")
        minx, miny, maxx, maxy = first_wgs84.total_bounds
        centre = [(miny + maxy) / 2.0, (minx + maxx) / 2.0]

        fmap = folium.Map(location=centre, zoom_start=13, tiles="OpenStreetMap")

        for name, layer, style in self.layers:
            wgs84 = layer.to_crs("EPSG:4326")
            folium.GeoJson(
                data=wgs84.to_json(),
                name=name,
                style_function=lambda _feature, layer_style=style: layer_style or {
                    "weight": 2,
                    "fillOpacity": 0.25,
                },
                marker=folium.CircleMarker(radius=4, weight=1, fill=True, fill_opacity=0.8),
            ).add_to(fmap)

        folium.LayerControl().add_to(fmap)
        self._save_and_load(fmap)

    def _save_and_load(self, fmap: folium.Map) -> None:
        fmap.save(str(self.html_path))

        if QWebEngineView is not None:
            self.web_view.load(QUrl.fromLocalFile(str(self.html_path)))
        else:
            self.web_view.setText(f"Map HTML written to:\n{self.html_path}")
