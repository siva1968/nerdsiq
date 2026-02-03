"""Authentication router."""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, WordPressAuthRequest
from app.security import rate_limiter, token_blacklist, InputValidator

router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is blacklisted (logged out)
    if token_blacklist.is_blacklisted(token):
        raise credentials_exception
    
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Validate email format
    if not InputValidator.is_valid_email(email):
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    
    Uses OAuth2 password flow with email as username.
    Accepts form data (application/x-www-form-urlencoded).
    """
    # Check for brute force block
    is_blocked, retry_after = rate_limiter.is_blocked(request)
    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {retry_after} seconds.",
        )
    
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        rate_limiter.record_failed_login(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Clear failed login attempts on success
    rate_limiter.clear_failed_logins(request)
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(access_token=access_token)


@router.post("/login/json", response_model=TokenResponse)
async def login_json(
    http_request: Request,
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    
    Accepts JSON body with username/password.
    """
    # Check for brute force block
    is_blocked, retry_after = rate_limiter.is_blocked(http_request)
    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {retry_after} seconds.",
        )
    
    result = await db.execute(select(User).where(User.email == request.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.hashed_password):
        rate_limiter.record_failed_login(http_request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Clear failed login attempts on success
    rate_limiter.clear_failed_logins(http_request)
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Logout user by blacklisting their token."""
    # Decode token to get expiry
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        exp = payload.get("exp", 0)
        token_blacklist.add(token, exp)
    except JWTError:
        pass  # Token invalid anyway
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.post("/wp-sso", response_model=TokenResponse)
async def wordpress_sso(
    request: WordPressAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    WordPress Single Sign-On endpoint.
    
    WordPress calls this endpoint with a shared secret to get a JWT token
    for a logged-in WordPress user. Auto-creates the user if they don't exist.
    """
    # Verify the shared secret
    if not settings.wp_auth_secret or request.wp_secret != settings.wp_auth_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WordPress authentication",
        )
    
    # Find or create user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Auto-create user from WordPress
        user = User(
            email=request.email,
            hashed_password="",  # No password - WP SSO only
            full_name=request.display_name or request.email.split("@")[0],
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Create JWT token
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(access_token=access_token)
