"""
Local authentication service for self-hosted deployment.

Provides username/password authentication without relying on Privy.
"""

from sqlalchemy.orm import Session

from hyper_trader_api.models.user import User
from hyper_trader_api.utils.crypto import hash_password, verify_password


class LocalAuthService:
    """
    Service for local username/password authentication.

    Used in self-hosted mode instead of Privy authentication.
    """

    def __init__(self, db: Session):
        """
        Initialize local auth service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def system_initialized(self) -> bool:
        """
        Check if the system has been initialized with at least one user.

        Returns:
            True if any user exists, False otherwise
        """
        user = self.db.query(User).first()
        return user is not None

    def bootstrap_admin(self, username: str, password: str) -> User:
        """
        Create the first admin user during system bootstrap.

        This can only be called once - when no users exist in the system.
        Subsequent calls will raise ValueError.

        Args:
            username: Admin username (min 3 characters)
            password: Admin password (min 8 characters)

        Returns:
            Created admin User object

        Raises:
            ValueError: If system is already initialized or validation fails
        """
        # Check if system is already initialized
        if self.system_initialized():
            raise ValueError("System already initialized - cannot create bootstrap admin")

        # Validate username
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")

        # Validate password
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Create admin user
        password_hash = hash_password(password)
        user = User(
            username=username,
            password_hash=password_hash,
            is_admin=True,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def authenticate(self, username: str, password: str) -> User | None:
        """
        Authenticate a user with username and password.

        Args:
            username: Username to authenticate
            password: Password to verify

        Returns:
            User object if authentication succeeds, None otherwise
        """
        # Validate input
        if not username or not password:
            return None

        # Look up user by username
        user = self.db.query(User).filter_by(username=username).first()
        if not user:
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            return None

        return user
