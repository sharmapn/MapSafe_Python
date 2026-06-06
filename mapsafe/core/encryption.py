from __future__ import annotations

from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet


def generate_key() -> bytes:
    """Generate a Fernet-compatible symmetric key."""
    return Fernet.generate_key()


def encrypt_file(
    input_path: str | Path,
    output_path: Optional[str | Path] = None,
    key_path: Optional[str | Path] = None,
) -> tuple[Path, Path]:
    """Encrypt a file and save the encryption key beside it unless supplied."""
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.with_suffix(input_path.suffix + ".mapsafe.enc")
    else:
        output_path = Path(output_path)

    if key_path is None:
        key_path = input_path.with_suffix(input_path.suffix + ".mapsafe.key")
    else:
        key_path = Path(key_path)

    key = generate_key()
    encrypted = Fernet(key).encrypt(input_path.read_bytes())

    output_path.write_bytes(encrypted)
    key_path.write_bytes(key)

    return output_path, key_path


def decrypt_file(
    encrypted_path: str | Path,
    key_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> Path:
    """Decrypt a MapSafe encrypted file."""
    encrypted_path = Path(encrypted_path)
    key_path = Path(key_path)

    if output_path is None:
        output_path = encrypted_path.with_suffix(".decrypted")
    else:
        output_path = Path(output_path)

    key = key_path.read_bytes()
    decrypted = Fernet(key).decrypt(encrypted_path.read_bytes())
    output_path.write_bytes(decrypted)

    return output_path
