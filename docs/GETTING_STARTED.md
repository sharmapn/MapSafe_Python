# Getting started with MapSafe Python

This is the first standalone desktop version of MapSafe.

## Layout

The application uses a permanent two-panel layout:

- Left panel: controls for data loading, geomasking, H3 binning, encryption, receipt generation, and decryption.
- Right panel: map display that remains visible while the user works through the controls.

## Install

Create and activate a virtual environment.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Current features

- Load GeoJSON, Shapefile, GeoPackage, and zipped Shapefile where supported by GeoPandas.
- Display the loaded layer in the right-side map panel.
- Run point geomasking using minimum and maximum masking distance in metres.
- Calculate a Spruill-style privacy rating.
- Run H3 hexagonal binning for point datasets.
- Save outputs as GeoJSON.
- Encrypt the latest output or current layer.
- Create a local SHA-256 receipt.
- Decrypt encrypted MapSafe files using the saved key.

## Notes

This version removes the QGIS dependency. It uses PyQt5, PyQtWebEngine, GeoPandas, Shapely, Folium, H3, SciPy, NumPy, and Cryptography.

The blockchain notarisation function is currently represented by a local SHA-256 receipt. The same hash can later be submitted to a Sepolia/Ethereum smart contract or another blockchain backend.
