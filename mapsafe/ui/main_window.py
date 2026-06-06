"""Main window for the MapSafe Python desktop application.

This module builds the main two-panel user interface:

- the left panel contains the workflow controls; and
- the right panel always shows the map.

The file is intentionally commented in detail so the UI workflow can be followed
by future contributors and students.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import geopandas as gpd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mapsafe.core.binning import h3_bin_points
from mapsafe.core.encryption import decrypt_file, encrypt_file
from mapsafe.core.io import default_output_path, load_vector_layer, save_vector_layer
from mapsafe.core.masking import mask_points
from mapsafe.core.notarisation import create_local_receipt
from mapsafe.ui.map_view import MapView


class MainWindow(QMainWindow):
    """Main standalone MapSafe window with left controls and right map."""

    def __init__(self):
        """Create the window, initialise state variables, and build the layout."""
        super().__init__()

        # Window title shown by the operating system.
        self.setWindowTitle("MapSafe Python - Standalone Geoprivacy Tool")

        # Current in-memory spatial layer. None means no layer has been loaded yet.
        self.current_gdf: Optional[gpd.GeoDataFrame] = None

        # Path of the original loaded dataset.
        self.current_path: Optional[Path] = None

        # Most recent output path. Encryption and receipt creation use this path.
        self.last_output_path: Optional[Path] = None

        # Right-side permanent map panel.
        self.map_view = MapView()

        # Bottom status text in the left panel.
        self.status_label = QLabel("Load a point layer to begin.")

        # Progress bar used for longer operations. It is placed at the bottom of
        # the left panel and is used for geomasking, encryption, and decryption.
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)

        # Splitter creates the left/right interface.
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([390, 1000])

        # Make the splitter the main content of the window.
        self.setCentralWidget(splitter)

        # Add the menu bar.
        self._build_menu()

    def _build_menu(self) -> None:
        """Create the top File menu."""
        file_menu = self.menuBar().addMenu("&File")

        # Menu action for loading a vector file.
        open_action = QAction("Open vector layer", self)
        open_action.triggered.connect(self.load_layer)
        file_menu.addAction(open_action)

        # Menu action for closing the application.
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _build_left_panel(self) -> QWidget:
        """Build the scrollable left-side control panel."""
        container = QWidget()
        layout = QVBoxLayout(container)

        # Application heading.
        title = QLabel("MapSafe Python")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Short explanatory subtitle.
        subtitle = QLabel("Standalone geoprivacy controls")
        subtitle.setStyleSheet("color: #555;")
        layout.addWidget(subtitle)

        # Workflow tabs.
        tabs = QTabWidget()
        tabs.addTab(self._build_data_tab(), "Data")
        tabs.addTab(self._build_safeguard_tab(), "Safeguard")
        tabs.addTab(self._build_access_tab(), "Access")
        tabs.addTab(self._build_log_tab(), "Log")
        layout.addWidget(tabs)

        # Status and progress are deliberately placed at the bottom of the left
        # panel so they remain visible regardless of which tab is active.
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        # Scroll area keeps the left controls usable on smaller screens.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setMinimumWidth(360)
        scroll.setMaximumWidth(460)
        return scroll

    def _build_data_tab(self) -> QWidget:
        """Build the Data tab used for loading and saving layers."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Button for loading vector data.
        load_button = QPushButton("Load GeoJSON / Shapefile / GeoPackage")
        load_button.clicked.connect(self.load_layer)
        layout.addWidget(load_button)

        # Summary of currently loaded layer.
        self.layer_label = QLabel("No layer loaded.")
        self.layer_label.setWordWrap(True)
        layout.addWidget(self.layer_label)

        # Button for saving the current layer.
        save_button = QPushButton("Save current displayed layer as GeoJSON")
        save_button.clicked.connect(self.save_current_layer)
        layout.addWidget(save_button)

        layout.addStretch()
        return tab

    def _build_safeguard_tab(self) -> QWidget:
        """Build the Safeguard tab for masking, binning, encryption, and receipt creation."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Geomasking controls.
        masking_group = QGroupBox("Geomasking")
        masking_form = QFormLayout(masking_group)

        self.min_distance_spin = QDoubleSpinBox()
        self.min_distance_spin.setRange(0, 10_000_000)
        self.min_distance_spin.setDecimals(2)
        self.min_distance_spin.setValue(100.0)
        self.min_distance_spin.setSuffix(" m")

        self.max_distance_spin = QDoubleSpinBox()
        self.max_distance_spin.setRange(0.01, 10_000_000)
        self.max_distance_spin.setDecimals(2)
        self.max_distance_spin.setValue(500.0)
        self.max_distance_spin.setSuffix(" m")

        # This checkbox is the on/off toggle for the Spruill-style privacy score.
        self.calculate_privacy_check = QCheckBox("Calculate Spruill-style privacy rating")
        self.calculate_privacy_check.setChecked(True)

        masking_form.addRow("Minimum distance", self.min_distance_spin)
        masking_form.addRow("Maximum distance", self.max_distance_spin)
        masking_form.addRow(self.calculate_privacy_check)

        mask_button = QPushButton("Run geomasking")
        mask_button.clicked.connect(self.run_geomasking)
        masking_form.addRow(mask_button)

        self.privacy_label = QLabel("Privacy rating: -")
        masking_form.addRow(self.privacy_label)
        layout.addWidget(masking_group)

        # H3 binning controls.
        h3_group = QGroupBox("H3 hexagonal binning")
        h3_form = QFormLayout(h3_group)

        self.h3_resolution_spin = QSpinBox()
        self.h3_resolution_spin.setRange(0, 15)
        self.h3_resolution_spin.setValue(7)

        h3_button = QPushButton("Run H3 binning")
        h3_button.clicked.connect(self.run_h3_binning)

        h3_form.addRow("Resolution", self.h3_resolution_spin)
        h3_form.addRow(h3_button)
        layout.addWidget(h3_group)

        # File protection actions.
        encrypt_button = QPushButton("Encrypt last output/current layer")
        encrypt_button.clicked.connect(self.encrypt_current_file)
        layout.addWidget(encrypt_button)

        notarise_button = QPushButton("Create local SHA-256 receipt")
        notarise_button.clicked.connect(self.notarise_current_file)
        layout.addWidget(notarise_button)

        layout.addStretch()
        return tab

    def _build_access_tab(self) -> QWidget:
        """Build the Access tab used for decryption."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        decrypt_group = QGroupBox("Decrypt MapSafe file")
        form = QFormLayout(decrypt_group)

        self.encrypted_file_label = QLabel("No encrypted file selected.")
        self.encrypted_file_label.setWordWrap(True)

        self.key_file_label = QLabel("No key file selected.")
        self.key_file_label.setWordWrap(True)

        encrypted_button = QPushButton("Choose encrypted file")
        encrypted_button.clicked.connect(self.choose_encrypted_file)

        key_button = QPushButton("Choose key file")
        key_button.clicked.connect(self.choose_key_file)

        decrypt_button = QPushButton("Decrypt file")
        decrypt_button.clicked.connect(self.decrypt_selected_file)

        form.addRow(encrypted_button)
        form.addRow(self.encrypted_file_label)
        form.addRow(key_button)
        form.addRow(self.key_file_label)
        form.addRow(decrypt_button)

        # These are set only after the user chooses the files.
        self.encrypted_path: Optional[Path] = None
        self.key_path: Optional[Path] = None

        layout.addWidget(decrypt_group)
        layout.addStretch()
        return tab

    def _build_log_tab(self) -> QWidget:
        """Build the Log tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        return tab

    def _set_progress(self, value: int, message: Optional[str] = None) -> None:
        """Set the progress bar value and optionally update the status message.

        The current implementation uses a simple 0/50/100 progress pattern:

        - 0% means the operation has started;
        - 50% means the operation is processing; and
        - 100% means the operation has completed.

        QApplication.processEvents() is called so the progress bar visually
        updates even though these first-version operations run on the main UI thread.
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(value)

        if message:
            self.status_label.setText(message)

        QApplication.processEvents()

    def _reset_progress(self) -> None:
        """Reset and hide the progress bar when no progress should be shown."""
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        QApplication.processEvents()

    def load_layer(self) -> None:
        """Open a vector layer and display it on the map."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open vector layer",
            "",
            "Vector files (*.geojson *.json *.shp *.gpkg *.zip);;All files (*.*)",
        )

        if not path:
            return

        try:
            self.current_gdf = load_vector_layer(path)
            self.current_path = Path(path)
            self.last_output_path = self.current_path

            self.layer_label.setText(
                f"Loaded: {self.current_path.name}\n"
                f"Features: {len(self.current_gdf)}\n"
                f"CRS: {self.current_gdf.crs}"
            )

            self.map_view.set_layer("Original layer", self.current_gdf)
            self._log(f"Loaded layer: {self.current_path}")
            self.status_label.setText("Layer loaded. Use the Safeguard tab to mask or bin.")
            self._reset_progress()

        except Exception as exc:
            self._show_error("Could not load layer", exc)

    def save_current_layer(self) -> None:
        """Save the current in-memory layer to a user-selected path."""
        if self.current_gdf is None:
            self._warn("Please load or create a layer first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save current layer",
            "",
            "GeoJSON (*.geojson);;GeoPackage (*.gpkg);;Shapefile (*.shp)",
        )

        if not path:
            return

        try:
            saved_path = save_vector_layer(self.current_gdf, path)
            self.last_output_path = saved_path
            self._log(f"Saved current layer: {saved_path}")
            self.status_label.setText(f"Saved: {saved_path.name}")

        except Exception as exc:
            self._show_error("Could not save layer", exc)

    def run_geomasking(self) -> None:
        """Run geomasking on the currently active layer."""
        if self.current_gdf is None or self.current_path is None:
            self._warn("Please load a point layer first.")
            return

        try:
            # 0%: operation has started.
            self._set_progress(0, "Starting geomasking...")

            original_gdf = self.current_gdf

            # 50%: actual processing is about to run. For large datasets this is
            # where most time may be spent, especially if the Spruill option is on.
            self._set_progress(50, "Geomasking in progress...")
            masked_gdf, report = mask_points(
                original_gdf,
                min_distance=self.min_distance_spin.value(),
                max_distance=self.max_distance_spin.value(),
                calculate_privacy_rating=self.calculate_privacy_check.isChecked(),
            )

            output_path = default_output_path(self.current_path, "_masked")
            save_vector_layer(masked_gdf, output_path)

            self.map_view.set_layer("Original layer", original_gdf)
            self.map_view.add_layer(
                "Masked layer",
                masked_gdf,
                style={"color": "#0B6623", "weight": 2, "fillOpacity": 0.25},
            )

            self.current_gdf = masked_gdf
            self.last_output_path = output_path

            if report.privacy_rating is None:
                self.privacy_label.setText("Privacy rating: not calculated")
            else:
                self.privacy_label.setText(f"Privacy rating: {report.privacy_rating}/100")

            # 100%: operation completed successfully.
            self._set_progress(100, f"Geomasking complete: {output_path.name}")

            self._log(
                "Geomasking complete\n"
                f"  Output: {output_path}\n"
                f"  Features: {report.feature_count}\n"
                f"  Distance: {report.min_distance}m - {report.max_distance}m\n"
                f"  Privacy rating: {report.privacy_rating}\n"
                f"  Time: {report.elapsed_seconds}s"
            )

        except Exception as exc:
            self._set_progress(0, "Geomasking failed.")
            self._show_error("Geomasking failed", exc)

    def run_h3_binning(self) -> None:
        """Run H3 hexagonal binning on the currently active point layer."""
        if self.current_gdf is None or self.current_path is None:
            self._warn("Please load a point layer first.")
            return

        try:
            resolution = self.h3_resolution_spin.value()
            hex_gdf = h3_bin_points(self.current_gdf, resolution)

            output_path = default_output_path(self.current_path, f"_h3_r{resolution}")
            save_vector_layer(hex_gdf, output_path)

            self.map_view.set_layer(
                f"H3 bins r{resolution}",
                hex_gdf,
                style={"weight": 1, "fillOpacity": 0.45},
            )

            self.current_gdf = hex_gdf
            self.last_output_path = output_path

            self.status_label.setText(f"H3 binning complete: {output_path.name}")
            self._log(
                "H3 binning complete\n"
                f"  Output: {output_path}\n"
                f"  Hexagons: {len(hex_gdf)}\n"
                f"  Resolution: {resolution}"
            )

        except Exception as exc:
            self._show_error("H3 binning failed", exc)

    def encrypt_current_file(self) -> None:
        """Encrypt the most recent output file, or the loaded source file."""
        source_path = self.last_output_path or self.current_path

        if source_path is None:
            self._warn("Please load, mask, or bin a file first.")
            return

        try:
            # 0%: encryption started.
            self._set_progress(0, "Starting encryption...")

            # 50%: encryption processing.
            self._set_progress(50, "Encryption in progress...")
            encrypted_path, key_path = encrypt_file(source_path)

            # 100%: encryption complete.
            self._set_progress(100, f"Encrypted: {encrypted_path.name}")

            self._log(
                "Encryption complete\n"
                f"  Encrypted file: {encrypted_path}\n"
                f"  Key file: {key_path}"
            )

            QMessageBox.information(
                self,
                "Encryption complete",
                f"Encrypted file:\n{encrypted_path}\n\nKey file:\n{key_path}",
            )

        except Exception as exc:
            self._set_progress(0, "Encryption failed.")
            self._show_error("Encryption failed", exc)

    def notarise_current_file(self) -> None:
        """Create a local SHA-256 receipt for the most recent file."""
        source_path = self.last_output_path or self.current_path

        if source_path is None:
            self._warn("Please load, mask, or bin a file first.")
            return

        try:
            receipt_path, receipt = create_local_receipt(source_path)
            self.status_label.setText(f"Receipt created: {receipt_path.name}")
            self._log(
                "Local receipt created\n"
                f"  Receipt: {receipt_path}\n"
                f"  SHA-256: {receipt['sha256']}"
            )
            QMessageBox.information(
                self,
                "Receipt created",
                f"Receipt file:\n{receipt_path}\n\nSHA-256:\n{receipt['sha256']}",
            )

        except Exception as exc:
            self._show_error("Receipt creation failed", exc)

    def choose_encrypted_file(self) -> None:
        """Ask the user to select a MapSafe encrypted file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose encrypted file",
            "",
            "Encrypted files (*.enc);;All files (*.*)",
        )

        if path:
            self.encrypted_path = Path(path)
            self.encrypted_file_label.setText(str(self.encrypted_path))

    def choose_key_file(self) -> None:
        """Ask the user to select the Fernet key file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose key file",
            "",
            "Key files (*.key);;All files (*.*)",
        )

        if path:
            self.key_path = Path(path)
            self.key_file_label.setText(str(self.key_path))

    def decrypt_selected_file(self) -> None:
        """Decrypt the encrypted/key pair selected in the Access tab."""
        if self.encrypted_path is None or self.key_path is None:
            self._warn("Please choose both the encrypted file and key file.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save decrypted file",
            "",
            "All files (*.*)",
        )

        if not output_path:
            return

        try:
            # 0%: decryption started.
            self._set_progress(0, "Starting decryption...")

            # 50%: decryption processing.
            self._set_progress(50, "Decryption in progress...")
            decrypted_path = decrypt_file(self.encrypted_path, self.key_path, output_path)

            # 100%: decryption complete.
            self._set_progress(100, f"Decrypted: {decrypted_path.name}")

            self._log(f"Decryption complete: {decrypted_path}")

        except Exception as exc:
            self._set_progress(0, "Decryption failed.")
            self._show_error("Decryption failed", exc)

    def _log(self, message: str) -> None:
        """Append a message to the Log tab."""
        self.log_box.append(message)
        self.log_box.append("")

    def _warn(self, message: str) -> None:
        """Show a warning dialog."""
        QMessageBox.warning(self, "MapSafe Python", message)

    def _show_error(self, title: str, exc: Exception) -> None:
        """Log and display an error dialog."""
        self._log(f"{title}: {exc}")
        QMessageBox.critical(self, title, str(exc))
