# MapSafe Python

A standalone Python desktop implementation of **MapSafe**, designed to bring the core geoprivacy workflow of the original QGIS plugin into a lightweight Python application.

The main design goal is a clear two-panel desktop interface:

- **Left panel**: all user controls, parameters, file actions, and status messages.
- **Right panel**: an always-visible interactive map showing the loaded layer and generated outputs.

This standalone version is intended to make MapSafe easier to test, demonstrate, package, and extend outside the QGIS plugin environment.

## Background

This project is a standalone companion to the original MapSafe QGIS plugin:

https://github.com/sharmapn/MapSafe-QGIS-plugin

The QGIS plugin is appropriate when users are already working inside QGIS. This standalone Python version is useful when the goal is to provide a focused geoprivacy tool that does not require opening a full GIS platform.

## Purpose

MapSafe Python provides a desktop environment for applying and demonstrating common geoprivacy operations, including:

- geomasking sensitive point data,
- aggregating point data into H3 hexagonal bins,
- encrypting protected outputs,
- creating a local SHA-256 receipt,
- decrypting protected files,
- viewing spatial outputs directly in the application map panel.

## Current UI layout

The application uses a fixed left-right layout.

### Left panel

The left panel contains the workflow controls. It is organised into tabs.

#### Data tab

The Data tab is used to:

- load vector spatial data,
- display the loaded file name,
- display feature count,
- display coordinate reference system,
- save the current displayed layer.

#### Safeguard tab

The Safeguard tab is used to:

- run geomasking,
- set minimum and maximum masking distances,
- calculate a Spruill-style privacy rating,
- run H3 hexagonal binning,
- set H3 resolution,
- encrypt the latest output or current file,
- create a local SHA-256 receipt.

#### Access tab

The Access tab is used to:

- choose an encrypted MapSafe file,
- choose the corresponding key file,
- decrypt the protected file.

#### Log tab

The Log tab is used to:

- show process messages,
- show output paths,
- show operation summaries,
- help with debugging and verification.

### Right panel

The right panel always shows the map. It is used to:

- display the original layer,
- display the masked layer,
- display H3 binned output,
- keep the spatial context visible while the user changes controls in the left panel.

## Implemented features

### 1. Vector data loading

The application loads vector data using GeoPandas.

Supported formats depend on the installed GeoPandas/Fiona/GDAL environment, but commonly include:

- GeoJSON
- Shapefile
- GeoPackage
- zipped vector datasets where supported by the environment

When a file is loaded, the application displays:

- file name,
- number of features,
- CRS,
- map preview.

### 2. Interactive map display

The map panel is generated using Folium and displayed inside the desktop interface through PyQtWebEngine.

The map panel is designed to stay visible while the user navigates between the Data, Safeguard, Access, and Log tabs.

### 3. Geomasking

The geomasking function currently focuses on point datasets.

The process is:

1. Load a point layer.
2. Check that the dataset contains point geometry.
3. Convert the dataset to a metric working CRS if required.
4. Generate a random direction for each point.
5. Generate a random displacement distance between the selected minimum and maximum.
6. Move each point.
7. Reproject the masked output back to the original CRS.
8. Save the masked output.
9. Display the original and masked layers in the map panel.

### 4. Spruill-style privacy rating

The application includes a simplified Spruill-style privacy rating.

The process is:

1. Compare each masked point against the original dataset.
2. Find the nearest original point.
3. Check whether the nearest original point is still the point's own original location.
4. Estimate the percentage of points that are no longer easily re-identified.
5. Report a privacy score from 0 to 100.

A higher score indicates stronger location privacy.

### 5. H3 hexagonal binning

The H3 binning function converts point data into hexagonal aggregation units.

The process is:

1. Convert the input point layer to WGS84 if required.
2. Convert each point to an H3 cell at the selected resolution.
3. Count the number of points in each cell.
4. Generate H3 polygon geometries.
5. Save the binned output as a vector layer.
6. Display the hexagonal bins on the map.

The output includes fields such as:

- H3 cell ID,
- point count,
- H3 resolution.

### 6. Encryption

The application supports file encryption using Fernet symmetric encryption from the Python `cryptography` package.

The process is:

1. Select the latest output or current file.
2. Generate an encryption key.
3. Encrypt the file.
4. Save the encrypted file.
5. Save the key file separately.

The encrypted file and key file must both be preserved. The encrypted file cannot be decrypted without the key file.

### 7. Local SHA-256 receipt

The application can create a local receipt for a file.

The receipt contains:

- tool name,
- receipt type,
- file name,
- file path,
- SHA-256 hash,
- UTC timestamp.

This is not yet blockchain notarisation. It is a local integrity receipt that can later be extended to a blockchain-backed notarisation workflow.

### 8. Decryption

The Access tab supports decrypting a protected file.

The process is:

1. Choose the encrypted file.
2. Choose the key file.
3. Select the output path.
4. Decrypt the file.
5. Save the decrypted output.

## Technical stack

The current standalone application uses:

- Python
- PyQt5
- PyQtWebEngine
- GeoPandas
- Shapely
- PyProj
- Folium
- H3
- NumPy
- SciPy
- cryptography

## Repository structure

```text
MapSafe_Python/
├── main.py
├── requirements.txt
├── README.md
├── docs/
│   └── GETTING_STARTED.md
└── mapsafe/
    ├── __init__.py
    ├── app.py
    ├── core/
    │   ├── io.py
    │   ├── masking.py
    │   ├── binning.py
    │   ├── encryption.py
    │   └── notarisation.py
    └── ui/
        ├── main_window.py
        └── map_view.py
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sharmapn/MapSafe_Python.git
cd MapSafe_Python
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

## Running the application

```bash
python main.py
```

## Typical workflows

### Workflow A: Load and view data

1. Open the application.
2. Go to the Data tab.
3. Click Load GeoJSON / Shapefile / GeoPackage.
4. Select a supported vector file.
5. Review the layer summary.
6. Inspect the layer in the map panel.

### Workflow B: Geomask a point dataset

1. Load a point dataset.
2. Go to the Safeguard tab.
3. Enter the minimum masking distance.
4. Enter the maximum masking distance.
5. Keep privacy rating enabled if required.
6. Click Run geomasking.
7. Review the masked layer in the map panel.
8. Save the result if needed.

### Workflow C: Create H3 bins

1. Load a point dataset.
2. Go to the Safeguard tab.
3. Select the H3 resolution.
4. Click Run H3 binning.
5. Review the hexagonal bin output in the map panel.
6. Save the result if needed.

### Workflow D: Encrypt an output

1. Create or load an output file.
2. Click Encrypt last output/current layer.
3. Save the encrypted file and key file.
4. Store the key file securely.

### Workflow E: Create a local receipt

1. Create or load an output file.
2. Click Create local SHA-256 receipt.
3. Store the generated receipt JSON file.
4. Use the receipt hash for later integrity checking.

### Workflow F: Decrypt a protected file

1. Go to the Access tab.
2. Choose the encrypted file.
3. Choose the key file.
4. Click Decrypt file.
5. Save the decrypted output.

## Example output files

The application may generate files such as:

```text
sample_points_masked.geojson
sample_points_h3_r7.geojson
sample_points_masked.geojson.mapsafe.enc
sample_points_masked.geojson.mapsafe.key
sample_points_masked.geojson.receipt.json
sample_points_masked_decrypted.geojson
```

## Notes on coordinate systems

Distance-based masking requires metre-based calculations.

If the input data is in a geographic CRS such as EPSG:4326, the app creates a projected working copy internally before applying displacement. The output is then returned to the original CRS.

## Notes on privacy and utility

The current version provides basic operational geoprivacy functions:

- random displacement,
- hexagonal aggregation,
- encryption,
- file integrity receipt generation.

It does not yet include advanced predictive masking, privacy-utility optimisation, or automatic masking-distance recommendation.

## Current limitations

This is an early standalone version. Current limitations include:

- geomasking is currently focused on point layers,
- H3 binning is currently focused on point layers,
- no full blockchain notarisation yet,
- no advanced role-based access workflow yet,
- no QGIS processing environment integration,
- no packaged executable installer yet,
- no advanced styling or dark mode yet,
- no multi-layer project/session management yet,
- no formal unit test suite yet.

## Planned next steps

Potential next steps include:

- add blockchain-backed notarisation,
- add sample datasets,
- add real screenshots,
- improve map symbology,
- add better legend control,
- add progress bars,
- add background task execution,
- add report export,
- package the app as a standalone executable,
- align more functions with the QGIS plugin,
- add unit tests,
- add CI workflow.

## Comparison with the QGIS plugin

### QGIS plugin

The QGIS plugin is:

- integrated directly into QGIS,
- based on QGIS APIs,
- suitable for users already working in QGIS,
- appropriate for full desktop GIS workflows.

### Standalone Python version

The standalone Python version is:

- independent of QGIS,
- lighter and easier to demonstrate,
- easier to package as a focused desktop tool,
- useful for separating core geoprivacy logic from QGIS-specific APIs.

## Development notes

The code is separated into two main layers.

### Core logic

Located in `mapsafe/core/`:

- `io.py` handles loading and saving vector data.
- `masking.py` handles point displacement and privacy rating.
- `binning.py` handles H3 bin generation.
- `encryption.py` handles file encryption and decryption.
- `notarisation.py` handles SHA-256 receipt generation.

### User interface

Located in `mapsafe/ui/`:

- `main_window.py` builds the left-panel controls.
- `map_view.py` manages the right-side map panel.

This separation makes it easier to improve or test the geoprivacy logic without rewriting the user interface.

## Troubleshooting

### PyQtWebEngine is missing

If the map panel does not render, install PyQtWebEngine:

```bash
pip install PyQtWebEngine
```

### GeoPandas installation issues

On some systems, GeoPandas dependencies can be easier to install through Conda:

```bash
conda create -n mapsafe-python python=3.11 geopandas pyqt folium shapely pyproj scipy numpy cryptography -c conda-forge
conda activate mapsafe-python
pip install h3 PyQtWebEngine
python main.py
```

### H3 binning does not work

Install or update the H3 Python package:

```bash
pip install --upgrade h3
```

### File does not display correctly

Check that:

- the dataset has valid geometry,
- the CRS is defined,
- the file format is supported by GeoPandas,
- the dataset is not empty.

## Acknowledgement

This standalone repository builds on the broader MapSafe geoprivacy work and the original MapSafe QGIS plugin.

Original plugin repository:

https://github.com/sharmapn/MapSafe-QGIS-plugin

## License

Please add the preferred open-source license before formal release.
