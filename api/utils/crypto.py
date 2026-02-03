"""
Cryptographic utilities for HyperTrader API.

Provides functions for:
- API key generation and verification (bcrypt)
- Password hashing and verification (bcrypt)
- Private key encryption/decryption (Fernet)
"""

import hashlib
import os
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

from api.config import get_settings


def generate_api_key() -> str:
    """
    Generate a new API key.

    Format: ht_<32-char-hex>

    Returns:
        str: API key in format ht_<hex>

    Example:
        >>> key = generate_api_key()
        >>> key.startswith("ht_")
        True
        >>> len(key)
        35
    """
    hex_part = secrets.token_hex(16)  # 32 hex characters
    return f"ht_{hex_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using bcrypt.

    Args:
        api_key: The plaintext API key to hash

    Returns:
        str: bcrypt hash of the API key
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(api_key.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_api_key(api_key: str, hashed: str) -> bool:
    """
    Verify an API key against its bcrypt hash.

    Args:
        api_key: The plaintext API key to verify
        hashed: The bcrypt hash to verify against

    Returns:
        bool: True if the API key matches, False otherwise
    """
    try:
        return bcrypt.checkpw(api_key.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plaintext password to hash

    Returns:
        str: bcrypt hash of the password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its bcrypt hash.

    Args:
        password: The plaintext password to verify
        hashed: The bcrypt hash to verify against

    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for database storage/lookup.
    
    This is used for refresh tokens where we need to store a hash
    for revocation checking, but don't need bcrypt's password-specific
    properties.
    
    Args:
        token: The token string to hash
        
    Returns:
        str: SHA-256 hex digest of the token
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_fernet() -> Fernet:
    """
    Get a Fernet instance using the ENCRYPTION_KEY from environment.

    The ENCRYPTION_KEY should be a valid Fernet key (base64-encoded 32 bytes).
    Generate one using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    Returns:
        Fernet: Fernet instance for encryption/decryption

    Raises:
        ValueError: If ENCRYPTION_KEY is not set or invalid
    """
    settings = get_settings()
    encryption_key = settings.encryption_key

    if not encryption_key:
        raise ValueError(
            "ENCRYPTION_KEY environment variable is not set. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    try:
        return Fernet(encryption_key.encode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid ENCRYPTION_KEY: {e}")


def encrypt_private_key(key: str) -> str:
    """
    Encrypt a private key using Fernet.

    Args:
        key: The private key to encrypt

    Returns:
        str: Encrypted private key (base64-encoded)

    Raises:
        ValueError: If encryption fails
    """
    fernet = get_fernet()
    encrypted = fernet.encrypt(key.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_private_key(encrypted: str) -> str:
    """
    Decrypt a private key using Fernet.

    Args:
        encrypted: The encrypted private key (base64-encoded)

    Returns:
        str: Decrypted private key

    Raises:
        ValueError: If decryption fails (invalid token or key)
    """
    fernet = get_fernet()
    try:
        decrypted = fernet.decrypt(encrypted.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        raise ValueError("Failed to decrypt private key: invalid token or key")


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    This is a helper function for documentation/setup purposes.

    Returns:
        str: Base64-encoded Fernet key

    Example:
        >>> key = generate_encryption_key()
        >>> len(key)
        44
    """
    return Fernet.generate_key().decode("utf-8")
