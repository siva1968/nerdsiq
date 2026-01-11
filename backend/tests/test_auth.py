"""Tests for authentication endpoints."""

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_db: AsyncSession) -> None:
    """Test successful login."""
    # Create test user
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    
    # Attempt login
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpassword123"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient) -> None:
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent@example.com", "password": "wrongpassword"},
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, test_db: AsyncSession) -> None:
    """Test login with inactive user account."""
    # Create inactive user
    user = User(
        email="inactive@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=False,
    )
    test_db.add(user)
    await test_db.commit()
    
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "inactive@example.com", "password": "testpassword123"},
    )
    
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_db: AsyncSession) -> None:
    """Test getting current user info with valid token."""
    # Create test user
    user = User(
        email="authtest@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Auth Test",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    
    # Login to get token
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "authtest@example.com", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    
    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "authtest@example.com"
    assert data["full_name"] == "Auth Test"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient) -> None:
    """Test getting current user with invalid token."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    
    assert response.status_code == 401
