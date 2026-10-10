"""Pydantic schemas for authentication request/response validation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
import re


# ── Registration ──────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters.")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username may only contain letters, numbers, underscores, and hyphens.")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v


# ── Login ─────────────────────────────────────────────────────

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Profile Update ────────────────────────────────────────────

class UserUpdateRequest(BaseModel):
    """PATCH /api/auth/me — only full_name is editable.
    Email changes require a separate secure verification flow not yet supported.
    """
    full_name: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) > 200:
                raise ValueError("Full name must be 200 characters or fewer.")
        return v if v else None


# ── Change Password ───────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    """POST /api/auth/change-password — secure password change flow."""
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long.")
        return v

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        new_pw = info.data.get("new_password")
        if new_pw and v != new_pw:
            raise ValueError("New passwords do not match.")
        return v


# ── Responses ─────────────────────────────────────────────────

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # Seconds until expiry
    user: UserResponse
