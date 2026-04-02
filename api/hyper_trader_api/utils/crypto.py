"""
Cryptography utilities for password hashing.

Uses bcrypt for password hashing.
"""

import bcrypt


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
