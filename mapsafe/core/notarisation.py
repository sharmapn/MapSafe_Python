"""Local receipt and file-integrity helpers for MapSafe Python.

The current standalone application does not yet submit hashes to a blockchain.
Instead, it creates a local SHA-256 receipt.  This is still useful because it
records the exact hash of a protected output file at a known time and provides a
foundation for later blockchain-backed notarisation.
"""

# Enable postponed type annotations for consistency with the rest of the package.
from __future__ import annotations

# hashlib provides standard cryptographic hash functions such as SHA-256.
import hashlib

# json is used to write the receipt as a human-readable JSON file.
import json

# datetime and timezone are used to store a UTC timestamp in the receipt.
from datetime import datetime, timezone

# Path gives safer cross-platform path handling than raw strings.
from pathlib import Path

# Optional is used for an output path that can be omitted by the caller.
from typing import Optional


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hash of a file.

    Args:
        path: Path to the file to hash.

    Returns:
        str: Hexadecimal SHA-256 digest.
    """

    # Convert the incoming path to a Path object for consistent file access.
    path = Path(path)

    # Create a new SHA-256 hash object.
    digest = hashlib.sha256()

    # Open the file in binary mode because hashes must be calculated from exact
    # bytes, not decoded text.
    with path.open("rb") as file_obj:
        # Read the file in 1 MB chunks.  This avoids loading very large spatial
        # files entirely into memory.
        for block in iter(lambda: file_obj.read(1024 * 1024), b""):
            # Add each block of bytes to the running hash.
            digest.update(block)

    # Return the final digest as a hexadecimal string.
    return digest.hexdigest()


def create_local_receipt(
    input_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> tuple[Path, dict]:
    """Create a local SHA-256 receipt for a file.

    Args:
        input_path: File to create a receipt for.
        output_path: Optional path for the receipt JSON file.  If omitted, the
            receipt is written beside the input file.

    Returns:
        tuple[Path, dict]: The receipt path and the receipt dictionary.
    """

    # Normalise the input path so path operations are consistent.
    input_path = Path(input_path)

    # If the caller does not provide a receipt path, create one beside the input
    # file.  The original suffix is preserved before adding ``.receipt.json``.
    if output_path is None:
        output_path = input_path.with_suffix(input_path.suffix + ".receipt.json")
    else:
        output_path = Path(output_path)

    # Build the receipt dictionary.  This structure can later be extended with a
    # blockchain transaction hash or digital signature.
    receipt = {
        # Name of the tool that generated the receipt.
        "tool": "MapSafe Python",

        # Receipt type makes the file self-describing.
        "receipt_type": "local_sha256_receipt",

        # Store only the file name separately for quick display.
        "file_name": input_path.name,

        # Store the resolved absolute path for local traceability.
        "file_path": str(input_path.resolve()),

        # Store the SHA-256 hash of the exact file bytes.
        "sha256": sha256_file(input_path),

        # Store a timezone-aware UTC timestamp.
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }

    # Write the receipt as pretty-printed JSON so it is easy for users to inspect.
    output_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    # Return both the output path and the dictionary so the UI can display the
    # hash or receipt location without reading the file again.
    return output_path, receipt
