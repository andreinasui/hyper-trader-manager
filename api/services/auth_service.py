"""
Authentication service for HyperTrader API.

Handles user registration, API key generation and validation, password authentication.
"""

from typing import Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from api.models import User
from api.utils.crypto import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    hash_password,
    verify_password,
)


class AuthService:
    """
    Authentication service for user and API key management.

    This service handles:
    - User registration with initial API key or password
    - API key generation and rotation
    - API key validation
    - Password authentication
    """

    @staticmethod
    def register_user(
        db: Session,
        email: str,
        password: Optional[str] = None,
    ) -> Tuple[User, Optional[str]]:
        """
        Register a new user with either password or API key.

        Args:
            db: Database session
            email: User's email address
            password: Optional password for JWT authentication

        Returns:
            Tuple of (User, plaintext_api_key or None)

        Raises:
            ValueError: If email is already registered
        """
        # Check if user already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise ValueError(f"Email already registered: {email}")

        # Generate API key only if no password provided
        api_key = None
        api_key_hash = None
        password_hash_value = None

        if password:
            # Password-based authentication
            password_hash_value = hash_password(password)
        else:
            # API-key-based authentication (backward compatibility)
            api_key = generate_api_key()
            api_key_hash = hash_api_key(api_key)

        # Create user
        user = User(
            email=email,
            api_key_hash=api_key_hash,
            password_hash=password_hash_value,
            plan_tier="free",
            is_admin=False,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user, api_key

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Args:
            db: Database session
            email: User's email
            password: User's password

        Returns:
            User if authentication successful, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()

        if not user or not user.password_hash:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    def generate_new_api_key(db: Session, user_id: uuid.UUID) -> str:
        """
        Generate a new API key for an existing user.

        This invalidates the previous API key.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            str: New plaintext API key

        Raises:
            ValueError: If user not found
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Generate new API key
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)

        # Update user
        user.api_key_hash = api_key_hash
        db.commit()

        return api_key

    @staticmethod
    def get_user_by_api_key(db: Session, api_key: str) -> Optional[User]:
        """
        Validate an API key and return the associated user.

        This is an O(n) operation as we need to check all users.
        For production with many users, consider using a hash prefix index.

        Args:
            db: Database session
            api_key: Plaintext API key to validate

        Returns:
            User if valid, None if invalid
        """
        # Get all users and check API key
        # Note: This is O(n) - for large user bases, consider caching or hash prefix lookup
        users = db.query(User).all()

        for user in users:
            if verify_api_key(api_key, user.api_key_hash):
                return user

        return None
