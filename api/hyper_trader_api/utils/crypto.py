"""
Cryptography utilities for password hashing and secret encryption.

Uses:
- bcrypt for password hashing
- cryptography Fernet for symmetric secret encryption
"""

import bcrypt
from cryptography.fernet import Fernet


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt password hash string
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Plain text password to verify
        password_hash: Bcrypt hash to verify against

    Returns:
        True if password matches hash, False otherwise
    """
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        # Invalid hash format or other verification errors
        return False


def encrypt_secret(plaintext: str, key: str) -> str:
    """
    Encrypt a secret using Fernet symmetric encryption.

    Args:
        plaintext: Plain text secret to encrypt
        key: Base64-encoded 32-byte encryption key

    Returns:
        Encrypted ciphertext as base64 string

    Raises:
        ValueError: If key is invalid format
    """
    try:
        # Ensure key is bytes
        if isinstance(key, str):
            key_bytes = key.encode()
        else:
            key_bytes = key

        f = Fernet(key_bytes)
        ciphertext_bytes = f.encrypt(plaintext.encode())
        return ciphertext_bytes.decode()
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}") from e


def decrypt_secret(ciphertext: str, key: str) -> str:
    """
    Decrypt a secret using Fernet symmetric encryption.

    Args:
        ciphertext: Encrypted ciphertext as base64 string
        key: Base64-encoded 32-byte encryption key

    Returns:
        Decrypted plaintext string

    Raises:
        ValueError: If key is invalid or decryption fails
    """
    try:
        # Ensure key is bytes
        if isinstance(key, str):
            key_bytes = key.encode()
        else:
            key_bytes = key

        f = Fernet(key_bytes)
        plaintext_bytes = f.decrypt(ciphertext.encode())
        return plaintext_bytes.decode()
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}") from e
