"""Authentication schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    username: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class TokenResponse(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """User creation schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserResponse(BaseModel):
    """User response schema."""

    id: int
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
