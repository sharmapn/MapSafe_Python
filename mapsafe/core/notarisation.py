from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hash of a file."""
    path = Path(path)
    digest = hashlib.sha256()

    with path.open("rb") as file_obj:
        for block in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def create_local_receipt(
    input_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> tuple[Path, dict]:
    """Create a local notarisation receipt."""
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.with_suffix(input_path.suffix + ".receipt.json")
    else:
        output_path = Path(output_path)

    receipt = {
        "tool": "MapSafe Python",
        "receipt_type": "local_sha256_receipt",
        "file_name": input_path.name,
        "file_path": str(input_path.resolve()),
        "sha256": sha256_file(input_path),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }

    output_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return output_path, receipt
