"""
Utility functions for HyperTrader API.

This package exports crypto utilities for API key handling and encryption.
"""

from api.utils.crypto import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    get_fernet,
    encrypt_private_key,
    decrypt_private_key,
    generate_encryption_key,
)

__all__ = [
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "get_fernet",
    "encrypt_private_key",
    "decrypt_private_key",
    "generate_encryption_key",
]
