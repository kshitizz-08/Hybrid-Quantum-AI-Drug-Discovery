"""
Authentication service.

Handles password hashing/verification and JWT token lifecycle.
Never stores plain-text passwords.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.base import User

logger = logging.getLogger(__name__)
settings = get_settings()

# bcrypt context — auto-upgrades hashes on login if rounds change
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password Utilities ────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Utilities ─────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Claims to encode (typically {"sub": user_id}).
        expires_delta: Override the default expiry duration.

    Returns:
        Signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Returns the payload dict on success, None on failure.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        return None


# ── User Lookup ───────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Validate credentials and return the User if correct, else None.
    Timing is constant regardless of whether the user exists (no oracle).
    """
    user = get_user_by_email(db, email)
    if not user:
        # Still run hash to prevent timing attacks
        pwd_context.dummy_verify()
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_user(db: Session, email: str, username: str, password: str, full_name: Optional[str] = None) -> User:
    """
    Create and persist a new user with a hashed password.
    Raises ValueError if email or username already exists.
    """
    if get_user_by_email(db, email):
        raise ValueError(f"A user with email '{email}' already exists.")
    if get_user_by_username(db, username):
        raise ValueError(f"Username '{username}' is already taken.")

    user = User(
        email=email.lower().strip(),
        username=username.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("New user registered: id=%d, email=%s", user.id, user.email)
    return user


# ── Profile Update ────────────────────────────────────────────

def update_user_profile(db: Session, user: User, full_name: Optional[str]) -> User:
    """
    Update mutable profile fields (full_name only).
    Email changes require a separate verification flow and are not supported here.
    """
    if full_name is not None:
        user.full_name = full_name if full_name.strip() else None
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    logger.info("Profile updated: user_id=%d", user.id)
    return user


# ── Change Password ───────────────────────────────────────────

def change_user_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:
    """
    Validate current password then replace with a new bcrypt hash.

    Returns True on success.
    Raises ValueError if current_password is wrong or new password is the same.
    Never stores or logs plain-text passwords.
    """
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Current password is incorrect.")

    if verify_password(new_password, user.hashed_password):
        raise ValueError("New password must be different from the current password.")

    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    logger.info("Password changed: user_id=%d", user.id)
    return True
