"""File encryption and decryption helpers for MapSafe Python.

This module provides a simple symmetric-encryption workflow for protecting
MapSafe outputs.  It uses Fernet from the ``cryptography`` package, which gives
an authenticated encryption format: if the encrypted data is modified, decryption
will fail rather than silently producing corrupted output.
"""

# Enable postponed evaluation of type annotations.
from __future__ import annotations

# Path gives consistent filesystem handling across operating systems.
from pathlib import Path

# Optional is used for output paths that may be omitted by the caller.
from typing import Optional

# Fernet provides high-level symmetric authenticated encryption.
from cryptography.fernet import Fernet


def generate_key() -> bytes:
    """Generate a Fernet-compatible symmetric key.

    Returns:
        bytes: URL-safe base64-encoded key bytes suitable for Fernet.

    Important:
        The generated key must be saved securely.  Anyone with the encrypted file
        and this key can decrypt the data.
    """

    # Fernet.generate_key creates a new random key using secure randomness from
    # the operating system.
    return Fernet.generate_key()


def encrypt_file(
    input_path: str | Path,
    output_path: Optional[str | Path] = None,
    key_path: Optional[str | Path] = None,
) -> tuple[Path, Path]:
    """Encrypt a file and save the encryption key.

    Args:
        input_path: File to encrypt.
        output_path: Optional path for the encrypted file.  If omitted, a
            ``.mapsafe.enc`` suffix is added to the input filename.
        key_path: Optional path for the key file.  If omitted, a ``.mapsafe.key``
            suffix is added to the input filename.

    Returns:
        tuple[Path, Path]: Paths to the encrypted file and key file.
    """

    # Normalise the input path so later filesystem operations are consistent.
    input_path = Path(input_path)

    # If the caller did not provide an encrypted output path, create one beside
    # the input file.  The original suffix is preserved before adding
    # ``.mapsafe.enc`` so users can see the source file type.
    if output_path is None:
        output_path = input_path.with_suffix(input_path.suffix + ".mapsafe.enc")
    else:
        output_path = Path(output_path)

    # If the caller did not provide a key path, create one beside the input file.
    # The key file must be kept separate and protected by the user.
    if key_path is None:
        key_path = input_path.with_suffix(input_path.suffix + ".mapsafe.key")
    else:
        key_path = Path(key_path)

    # Generate a fresh encryption key for this file.
    key = generate_key()

    # Read the complete input file as bytes and encrypt it with Fernet.
    encrypted = Fernet(key).encrypt(input_path.read_bytes())

    # Write the encrypted bytes to disk.
    output_path.write_bytes(encrypted)

    # Write the key bytes to disk.  In a production workflow, this file should be
    # stored securely and access-controlled.
    key_path.write_bytes(key)

    # Return both paths so the UI can display them to the user.
    return output_path, key_path


def decrypt_file(
    encrypted_path: str | Path,
    key_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> Path:
    """Decrypt a MapSafe encrypted file.

    Args:
        encrypted_path: Path to the ``.mapsafe.enc`` file.
        key_path: Path to the matching ``.mapsafe.key`` file.
        output_path: Optional path for the decrypted output.

    Returns:
        Path: Path to the decrypted output file.
    """

    # Normalise the encrypted file path.
    encrypted_path = Path(encrypted_path)

    # Normalise the key file path.
    key_path = Path(key_path)

    # If no output path is provided, create a generic path based on the encrypted
    # filename.  The UI usually asks the user to choose a path explicitly.
    if output_path is None:
        output_path = encrypted_path.with_suffix(".decrypted")
    else:
        output_path = Path(output_path)

    # Read the saved Fernet key from disk.
    key = key_path.read_bytes()

    # Decrypt the encrypted file bytes.  If the wrong key is used, or if the file
    # has been tampered with, Fernet will raise an exception.
    decrypted = Fernet(key).decrypt(encrypted_path.read_bytes())

    # Write the decrypted bytes to the selected output path.
    output_path.write_bytes(decrypted)

    # Return the decrypted file path for status messages and logs.
    return output_path
