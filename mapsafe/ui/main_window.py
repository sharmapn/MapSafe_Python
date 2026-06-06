"""Main window for the MapSafe Python desktop application.

This module wires the user interface to the core geoprivacy functions.  The
window is deliberately split into two main areas:

1. a left control panel containing the workflow tabs; and
2. a right map panel that always remains visible.

The code below is commented in detail so students, researchers, and future
contributors can understand how the interface is connected to the processing
functions.
"""

# Enable postponed evaluation of type annotations.
from __future__ import annotations

# Path is used for storing and displaying selected file paths.
from pathlib import Path

# Optional marks variables that may not yet have a value, such as the currently
# loaded layer before the user opens a file.
from typing import Optional

# GeoPandas is used here only for type hints.  The actual geospatial operations
# are performed in mapsafe.core modules.
import geopandas as gpd

# Qt is used for layout orientation constants, such as Qt.Horizontal.
from PyQt5.QtCore import Qt

# Import the PyQt widgets used to build the desktop user interface.
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Core H3 aggregation function.
from mapsafe.core.binning import h3_bin_points

# Core encryption/decryption helpers.
from mapsafe.core.encryption import decrypt_file, encrypt_file

# Core vector file I/O helpers.
from mapsafe.core.io import default_output_path, load_vector_layer, save_vector_layer

# Core geomasking helper.
from mapsafe.core.masking import mask_points

# Core local SHA-256 receipt helper.
from mapsafe.core.notarisation import create_local_receipt

# Right-side map widget.
from mapsafe.ui.map_view import MapView


class MainWindow(QMainWindow):
    """Main standalone MapSafe window with left controls and right map."""

    def __init__(self):
        """Create the main application window and its two-panel layout."""

        # Initialise the QMainWindow parent class.
        super().__init__()

        # Set the title shown in the operating system window bar.
        self.setWindowTitle("MapSafe Python - Standalone Geoprivacy Tool")

        # Store the currently active spatial layer.  It starts as None because no
        # file has been loaded when the app first opens.
        self.current_gdf: Optional[gpd.GeoDataFrame] = None

        # Store the path of the source layer.  This is used to build default output
        # paths such as *_masked.geojson.
        self.current_path: Optional[Path] = None

        # Store the most recent file written or loaded.  Encryption and receipt
        # generation use this so they operate on the latest result.
        self.last_output_path: Optional[Path] = None

        # Create the permanent right-side map panel.
        self.map_view = MapView()

        # Status label shown at the bottom of the left panel.
        self.status_label = QLabel("Load a point layer to begin.")

        # QSplitter creates the left/right resizable layout.
        splitter = QSplitter(Qt.Horizontal)

        # Add the left workflow/control panel.
        splitter.addWidget(self._build_left_panel())

        # Add the right map panel.
        splitter.addWidget(self.map_view)

        # Keep the left panel relatively fixed while allowing the map to take most
        # of the extra space when the window is resized.
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Set the initial approximate width ratio: left panel around 390 px, map
        # panel around 1000 px.
        splitter.setSizes([390, 1000])

        # Put the splitter into the main window as the central widget.
        self.setCentralWidget(splitter)

        # Build the top menu bar.
        self._build_menu()

    def _build_menu(self) -> None:
        """Create the simple File menu."""

        # Add a File menu to the window menu bar.  The ampersand enables keyboard
        # shortcuts on platforms that support them.
        file_menu = self.menuBar().addMenu("&File")

        # Create a menu action for opening a vector layer.
        open_action = QAction("Open vector layer", self)

        # Connect the action to the same method used by the Data tab load button.
        open_action.triggered.connect(self.load_layer)

        # Add the Open action to the File menu.
        file_menu.addAction(open_action)

        # Create a menu action for closing the application.
        exit_action = QAction("Exit", self)

        # Connect the Exit action to the built-in close method.
        exit_action.triggered.connect(self.close)

        # Add the Exit action to the File menu.
        file_menu.addAction(exit_action)

    def _build_left_panel(self) -> QWidget:
        """Build the left-side control panel.

        Returns:
            QWidget: A scrollable left panel containing title, tabs, and status.
        """

        # Container holds all left-panel widgets.
        container = QWidget()

        # Vertical layout stacks title, subtitle, tabs, and status label.
        layout = QVBoxLayout(container)

        # Main left-panel title.
        title = QLabel("MapSafe Python")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Short subtitle explaining the purpose of the controls.
        subtitle = QLabel("Standalone geoprivacy controls")
        subtitle.setStyleSheet("color: #555;")
        layout.addWidget(subtitle)

        # QTabWidget groups the workflow into Data, Safeguard, Access, and Log.
        tabs = QTabWidget()
        tabs.addTab(self._build_data_tab(), "Data")
        tabs.addTab(self._build_safeguard_tab(), "Safeguard")
        tabs.addTab(self._build_access_tab(), "Access")
        tabs.addTab(self._build_log_tab(), "Log")

        # Add the tabs and bottom status label to the left panel.
        layout.addWidget(tabs)
        layout.addWidget(self.status_label)

        # Wrap the left panel in a scroll area so smaller screens can still reach
        # all controls.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        # Set practical width limits so the map panel remains dominant.
        scroll.setMinimumWidth(360)
        scroll.setMaximumWidth(460)

        # Return the scrollable panel to the main splitter.
        return scroll

    def _build_data_tab(self) -> QWidget:
        """Build the Data tab used for loading and saving layers."""

        # Create tab widget and vertical layout.
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Button for opening supported vector files.
        load_button = QPushButton("Load GeoJSON / Shapefile / GeoPackage")
        load_button.clicked.connect(self.load_layer)
        layout.addWidget(load_button)

        # Label used to display the currently loaded layer summary.
        self.layer_label = QLabel("No layer loaded.")
        self.layer_label.setWordWrap(True)
        layout.addWidget(self.layer_label)

        # Button for saving whichever layer is currently active in memory.
        save_button = QPushButton("Save current displayed layer as GeoJSON")
        save_button.clicked.connect(self.save_current_layer)
        layout.addWidget(save_button)

        # Push controls to the top of the tab.
        layout.addStretch()

        # Return the finished Data tab.
        return tab

    def _build_safeguard_tab(self) -> QWidget:
        """Build the Safeguard tab for masking, binning, encryption, and receipts."""

        # Create tab widget and vertical layout.
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Group geomasking controls together in a labelled box.
        masking_group = QGroupBox("Geomasking")
        masking_form = QFormLayout(masking_group)

        # Numeric input for minimum masking distance in metres.
        self.min_distance_spin = QDoubleSpinBox()
        self.min_distance_spin.setRange(0, 10_000_000)
        self.min_distance_spin.setDecimals(2)
        self.min_distance_spin.setValue(100.0)
        self.min_distance_spin.setSuffix(" m")

        # Numeric input for maximum masking distance in metres.
        self.max_distance_spin = QDoubleSpinBox()
        self.max_distance_spin.setRange(0.01, 10_000_000)
        self.max_distance_spin.setDecimals(2)
        self.max_distance_spin.setValue(500.0)
        self.max_distance_spin.setSuffix(" m")

        # Checkbox lets users skip privacy-rating calculation for faster runs.
        self.calculate_privacy_check = QCheckBox("Calculate Spruill-style privacy rating")
        self.calculate_privacy_check.setChecked(True)

        # Add geomasking inputs to the form layout.
        masking_form.addRow("Minimum distance", self.min_distance_spin)
        masking_form.addRow("Maximum distance", self.max_distance_spin)
        masking_form.addRow(self.calculate_privacy_check)

        # Button that starts the geomasking workflow.
        mask_button = QPushButton("Run geomasking")
        mask_button.clicked.connect(self.run_geomasking)
        masking_form.addRow(mask_button)

        # Label updated after masking to show the privacy rating.
        self.privacy_label = QLabel("Privacy rating: -")
        masking_form.addRow(self.privacy_label)

        # Add the geomasking group to the Safeguard tab.
        layout.addWidget(masking_group)

        # Group H3 controls together in a labelled box.
        h3_group = QGroupBox("H3 hexagonal binning")
        h3_form = QFormLayout(h3_group)

        # Integer spin box for H3 resolution.  H3 supports 0 to 15.
        self.h3_resolution_spin = QSpinBox()
        self.h3_resolution_spin.setRange(0, 15)
        self.h3_resolution_spin.setValue(7)

        # Button that starts H3 binning.
        h3_button = QPushButton("Run H3 binning")
        h3_button.clicked.connect(self.run_h3_binning)

        # Add H3 widgets to the H3 form.
        h3_form.addRow("Resolution", self.h3_resolution_spin)
        h3_form.addRow(h3_button)

        # Add the H3 group to the Safeguard tab.
        layout.addWidget(h3_group)

        # Button for encrypting the latest output/current file.
        encrypt_button = QPushButton("Encrypt last output/current layer")
        encrypt_button.clicked.connect(self.encrypt_current_file)
        layout.addWidget(encrypt_button)

        # Button for creating a local SHA-256 receipt for the latest file.
        notarise_button = QPushButton("Create local SHA-256 receipt")
        notarise_button.clicked.connect(self.notarise_current_file)
        layout.addWidget(notarise_button)

        # Keep controls at the top of the tab.
        layout.addStretch()

        # Return the finished Safeguard tab.
        return tab

    def _build_access_tab(self) -> QWidget:
        """Build the Access tab for decrypting protected MapSafe files."""

        # Create tab widget and vertical layout.
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Group decryption controls in a labelled box.
        decrypt_group = QGroupBox("Decrypt MapSafe file")
        form = QFormLayout(decrypt_group)

        # Label displaying the selected encrypted file.
        self.encrypted_file_label = QLabel("No encrypted file selected.")
        self.encrypted_file_label.setWordWrap(True)

        # Label displaying the selected key file.
        self.key_file_label = QLabel("No key file selected.")
        self.key_file_label.setWordWrap(True)

        # Button for selecting the encrypted file.
        encrypted_button = QPushButton("Choose encrypted file")
        encrypted_button.clicked.connect(self.choose_encrypted_file)

        # Button for selecting the Fernet key file.
        key_button = QPushButton("Choose key file")
        key_button.clicked.connect(self.choose_key_file)

        # Button for starting decryption.
        decrypt_button = QPushButton("Decrypt file")
        decrypt_button.clicked.connect(self.decrypt_selected_file)

        # Add the decryption widgets to the form.
        form.addRow(encrypted_button)
        form.addRow(self.encrypted_file_label)
        form.addRow(key_button)
        form.addRow(self.key_file_label)
        form.addRow(decrypt_button)

        # Store selected encrypted/key paths.  They remain None until the user
        # chooses files.
        self.encrypted_path: Optional[Path] = None
        self.key_path: Optional[Path] = None

        # Add the decryption group and top-align it.
        layout.addWidget(decrypt_group)
        layout.addStretch()

        # Return the finished Access tab.
        return tab

    def _build_log_tab(self) -> QWidget:
        """Build the Log tab used for process messages."""

        # Create tab widget and vertical layout.
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Text box stores operation logs.  It is read-only so users cannot
        # accidentally edit process history.
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        # Return the finished Log tab.
        return tab

    def load_layer(self) -> None:
        """Open a vector layer and display it on the map."""

        # Show a file picker for common vector formats.
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open vector layer",
            "",
            "Vector files (*.geojson *.json *.shp *.gpkg *.zip);;All files (*.*)",
        )

        # If the user cancels the dialog, stop without doing anything.
        if not path:
            return

        try:
            # Load the selected file using the core I/O helper.
            self.current_gdf = load_vector_layer(path)

            # Store the selected path for output naming.
            self.current_path = Path(path)

            # The loaded file is currently the latest available file.
            self.last_output_path = self.current_path

            # Update the Data tab summary label.
            self.layer_label.setText(
                f"Loaded: {self.current_path.name}\n"
                f"Features: {len(self.current_gdf)}\n"
                f"CRS: {self.current_gdf.crs}"
            )

            # Display the loaded layer on the right map panel.
            self.map_view.set_layer("Original layer", self.current_gdf)

            # Record the operation in the Log tab.
            self._log(f"Loaded layer: {self.current_path}")

            # Update the bottom status message.
            self.status_label.setText("Layer loaded. Use the Safeguard tab to mask or bin.")

        # Any error is displayed in both the log and an error dialog.
        except Exception as exc:
            self._show_error("Could not load layer", exc)

    def save_current_layer(self) -> None:
        """Save the current in-memory layer to a user-selected path."""

        # There is nothing to save until a layer has been loaded or created.
        if self.current_gdf is None:
            self._warn("Please load or create a layer first.")
            return

        # Ask the user where to save the active layer.
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save current layer",
            "",
            "GeoJSON (*.geojson);;GeoPackage (*.gpkg);;Shapefile (*.shp)",
        )

        # Stop if the user cancels the dialog.
        if not path:
            return

        try:
            # Save the current GeoDataFrame using the core I/O helper.
            saved_path = save_vector_layer(self.current_gdf, path)

            # Mark the saved file as the latest output, so encryption/receipt
            # actions can use it.
            self.last_output_path = saved_path

            # Log and display save status.
            self._log(f"Saved current layer: {saved_path}")
            self.status_label.setText(f"Saved: {saved_path.name}")

        # Show any save error to the user.
        except Exception as exc:
            self._show_error("Could not save layer", exc)

    def run_geomasking(self) -> None:
        """Run geomasking on the currently active layer."""

        # Geomasking requires a loaded layer and its source path.
        if self.current_gdf is None or self.current_path is None:
            self._warn("Please load a point layer first.")
            return

        try:
            # Keep a reference to the original/current layer so it can be shown
            # alongside the masked layer on the map.
            original_gdf = self.current_gdf

            # Run the core geomasking function using values from the UI controls.
            masked_gdf, report = mask_points(
                original_gdf,
                min_distance=self.min_distance_spin.value(),
                max_distance=self.max_distance_spin.value(),
                calculate_privacy_rating=self.calculate_privacy_check.isChecked(),
            )

            # Create a default output path beside the source file.
            output_path = default_output_path(self.current_path, "_masked")

            # Save the masked GeoDataFrame to disk.
            save_vector_layer(masked_gdf, output_path)

            # Reset the map to show the original layer first.
            self.map_view.set_layer("Original layer", original_gdf)

            # Add the masked layer as a second layer, styled in green.
            self.map_view.add_layer(
                "Masked layer",
                masked_gdf,
                style={"color": "#0B6623", "weight": 2, "fillOpacity": 0.25},
            )

            # Make the masked output the current working layer.
            self.current_gdf = masked_gdf

            # Store the saved masked file as the latest output.
            self.last_output_path = output_path

            # Update the privacy label depending on whether the rating was calculated.
            if report.privacy_rating is None:
                self.privacy_label.setText("Privacy rating: not calculated")
            else:
                self.privacy_label.setText(f"Privacy rating: {report.privacy_rating}/100")

            # Update bottom status and log details.
            self.status_label.setText(f"Geomasking complete: {output_path.name}")
            self._log(
                "Geomasking complete\n"
                f"  Output: {output_path}\n"
                f"  Features: {report.feature_count}\n"
                f"  Distance: {report.min_distance}m - {report.max_distance}m\n"
                f"  Privacy rating: {report.privacy_rating}\n"
                f"  Time: {report.elapsed_seconds}s"
            )

        # Display geomasking failures such as unsupported geometry types.
        except Exception as exc:
            self._show_error("Geomasking failed", exc)

    def run_h3_binning(self) -> None:
        """Run H3 hexagonal binning on the currently active point layer."""

        # H3 binning requires a loaded layer and source path.
        if self.current_gdf is None or self.current_path is None:
            self._warn("Please load a point layer first.")
            return

        try:
            # Read the H3 resolution from the UI spin box.
            resolution = self.h3_resolution_spin.value()

            # Run the core H3 binning function.
            hex_gdf = h3_bin_points(self.current_gdf, resolution)

            # Create a default output path containing the H3 resolution.
            output_path = default_output_path(self.current_path, f"_h3_r{resolution}")

            # Save the H3 output layer.
            save_vector_layer(hex_gdf, output_path)

            # Display the H3 layer on the map.
            self.map_view.set_layer(
                f"H3 bins r{resolution}",
                hex_gdf,
                style={"weight": 1, "fillOpacity": 0.45},
            )

            # Make the H3 output the current active layer.
            self.current_gdf = hex_gdf

            # Store the H3 output path as the latest output.
            self.last_output_path = output_path

            # Update status and log details.
            self.status_label.setText(f"H3 binning complete: {output_path.name}")
            self._log(
                "H3 binning complete\n"
                f"  Output: {output_path}\n"
                f"  Hexagons: {len(hex_gdf)}\n"
                f"  Resolution: {resolution}"
            )

        # Display any H3 failure, such as missing h3 package or non-point geometry.
        except Exception as exc:
            self._show_error("H3 binning failed", exc)

    def encrypt_current_file(self) -> None:
        """Encrypt the most recent output file, or the loaded source file."""

        # Prefer the latest output, but fall back to the original loaded path.
        source_path = self.last_output_path or self.current_path

        # Encryption requires an existing file path.
        if source_path is None:
            self._warn("Please load, mask, or bin a file first.")
            return

        try:
            # Encrypt the file and generate/write the key file.
            encrypted_path, key_path = encrypt_file(source_path)

            # Update bottom status.
            self.status_label.setText(f"Encrypted: {encrypted_path.name}")

            # Log both output paths so users can find the encrypted data and key.
            self._log(
                "Encryption complete\n"
                f"  Encrypted file: {encrypted_path}\n"
                f"  Key file: {key_path}"
            )

            # Show a confirmation dialog because the key file is important.
            QMessageBox.information(
                self,
                "Encryption complete",
                f"Encrypted file:\n{encrypted_path}\n\nKey file:\n{key_path}",
            )

        # Display encryption errors.
        except Exception as exc:
            self._show_error("Encryption failed", exc)

    def notarise_current_file(self) -> None:
        """Create a local SHA-256 receipt for the most recent file."""

        # Prefer the latest output, but fall back to the original loaded path.
        source_path = self.last_output_path or self.current_path

        # Receipt generation requires an existing file path.
        if source_path is None:
            self._warn("Please load, mask, or bin a file first.")
            return

        try:
            # Create the JSON receipt and get both the path and dictionary.
            receipt_path, receipt = create_local_receipt(source_path)

            # Update bottom status.
            self.status_label.setText(f"Receipt created: {receipt_path.name}")

            # Log the receipt path and hash for verification.
            self._log(
                "Local receipt created\n"
                f"  Receipt: {receipt_path}\n"
                f"  SHA-256: {receipt['sha256']}"
            )

            # Show the receipt details in a confirmation dialog.
            QMessageBox.information(
                self,
                "Receipt created",
                f"Receipt file:\n{receipt_path}\n\nSHA-256:\n{receipt['sha256']}",
            )

        # Display receipt generation errors.
        except Exception as exc:
            self._show_error("Receipt creation failed", exc)

    def choose_encrypted_file(self) -> None:
        """Ask the user to select a MapSafe encrypted file."""

        # Open a file picker focused on encrypted files but allowing all files.
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose encrypted file",
            "",
            "Encrypted files (*.enc);;All files (*.*)",
        )

        # If the user selected a file, store and display the path.
        if path:
            self.encrypted_path = Path(path)
            self.encrypted_file_label.setText(str(self.encrypted_path))

    def choose_key_file(self) -> None:
        """Ask the user to select the Fernet key file."""

        # Open a file picker focused on key files but allowing all files.
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose key file",
            "",
            "Key files (*.key);;All files (*.*)",
        )

        # If the user selected a file, store and display the path.
        if path:
            self.key_path = Path(path)
            self.key_file_label.setText(str(self.key_path))

    def decrypt_selected_file(self) -> None:
        """Decrypt the encrypted/key pair selected in the Access tab."""

        # Both encrypted file and key file are required.
        if self.encrypted_path is None or self.key_path is None:
            self._warn("Please choose both the encrypted file and key file.")
            return

        # Ask the user where the decrypted output should be saved.
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save decrypted file",
            "",
            "All files (*.*)",
        )

        # Stop if the user cancels the save dialog.
        if not output_path:
            return

        try:
            # Run the core decryption helper.
            decrypted_path = decrypt_file(self.encrypted_path, self.key_path, output_path)

            # Update status and log.
            self.status_label.setText(f"Decrypted: {decrypted_path.name}")
            self._log(f"Decryption complete: {decrypted_path}")

        # Display decryption errors, such as wrong key or corrupted encrypted file.
        except Exception as exc:
            self._show_error("Decryption failed", exc)

    def _log(self, message: str) -> None:
        """Append a message to the Log tab.

        Args:
            message: Text to append.
        """

        # Add the message text.
        self.log_box.append(message)

        # Add a blank line for readability between operations.
        self.log_box.append("")

    def _warn(self, message: str) -> None:
        """Show a warning dialog.

        Args:
            message: Warning text to display.
        """

        # QMessageBox.warning provides a standard modal warning dialog.
        QMessageBox.warning(self, "MapSafe Python", message)

    def _show_error(self, title: str, exc: Exception) -> None:
        """Log and display an error dialog.

        Args:
            title: Dialog title and log prefix.
            exc: Exception object that caused the failure.
        """

        # Add the error to the Log tab so there is a persistent record.
        self._log(f"{title}: {exc}")

        # Show a modal error dialog to the user.
        QMessageBox.critical(self, title, str(exc))
