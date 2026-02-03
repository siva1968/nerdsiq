"""Security middleware and utilities for NerdsIQ API."""

import hashlib
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

from fastapi import HTTPException, Request, status
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """In-memory rate limiter using sliding window."""
    
    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.blocked_ips: dict[str, float] = {}  # IP -> block until timestamp
        self.failed_logins: dict[str, list[float]] = defaultdict(list)
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique identifier for the client (IP + optional user)."""
        # Get IP from X-Forwarded-For header (behind proxy) or client
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        # Include user identifier if authenticated
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
            return f"{ip}:{token_hash}"
        
        return ip
    
    def _clean_old_requests(self, key: str, window_seconds: int = 60):
        """Remove requests outside the time window."""
        cutoff = time.time() - window_seconds
        self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]
    
    def is_blocked(self, request: Request) -> tuple[bool, int]:
        """Check if client is temporarily blocked. Returns (blocked, retry_after)."""
        key = self._get_client_key(request)
        if key in self.blocked_ips:
            block_until = self.blocked_ips[key]
            if time.time() < block_until:
                return True, int(block_until - time.time())
            else:
                del self.blocked_ips[key]
        return False, 0
    
    def check_rate_limit(self, request: Request) -> tuple[bool, int, int]:
        """
        Check if request is within rate limits.
        Returns (allowed, remaining, reset_seconds).
        """
        key = self._get_client_key(request)
        self._clean_old_requests(key)
        
        limit = settings.rate_limit_per_minute
        current_count = len(self.requests[key])
        
        if current_count >= limit:
            return False, 0, 60
        
        self.requests[key].append(time.time())
        return True, limit - current_count - 1, 60
    
    def record_failed_login(self, request: Request):
        """Record a failed login attempt for brute force protection."""
        key = self._get_client_key(request)
        cutoff = time.time() - 900  # 15-minute window
        self.failed_logins[key] = [ts for ts in self.failed_logins[key] if ts > cutoff]
        self.failed_logins[key].append(time.time())
        
        # Block after 5 failed attempts in 15 minutes
        if len(self.failed_logins[key]) >= 5:
            self.blocked_ips[key] = time.time() + 900  # Block for 15 minutes
            logger.warning(f"Blocked IP {key} due to failed login attempts")
    
    def clear_failed_logins(self, request: Request):
        """Clear failed login attempts after successful login."""
        key = self._get_client_key(request)
        self.failed_logins.pop(key, None)


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Check if blocked
        is_blocked, retry_after = rate_limiter.is_blocked(request)
        if is_blocked:
            return Response(
                content='{"detail": "Too many failed attempts. Please try again later."}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                },
            )
        
        # Check rate limit
        allowed, remaining, reset = rate_limiter.check_rate_limit(request)
        
        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded. Please slow down."}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        
        return response


# ============================================================================
# Security Headers
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # Content Security Policy for API (restrictive)
        if not settings.is_development:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
        
        # HSTS (only in production with HTTPS)
        if not settings.is_development:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        # Remove server identification
        response.headers["Server"] = "NerdsIQ"
        
        return response


# ============================================================================
# Request Logging / Audit Trail
# ============================================================================

class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests for audit purposes."""
    
    SENSITIVE_PATHS = ["/api/v1/auth/login", "/api/v1/auth/wp-sso"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Get client info
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log request (don't log sensitive data)
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
            "user_agent": request.headers.get("User-Agent", "")[:100],
        }
        
        # Log at appropriate level based on status code
        if response.status_code >= 500:
            logger.error(f"Request failed: {log_data}")
        elif response.status_code >= 400:
            logger.warning(f"Client error: {log_data}")
        elif request.url.path not in ["/health", "/"]:
            logger.info(f"Request: {log_data}")
        
        return response


# ============================================================================
# Input Validation Utilities
# ============================================================================

class InputValidator:
    """Utility class for input validation and sanitization."""
    
    # Patterns for validation
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    UUID_PATTERN = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.I)
    
    # Dangerous patterns to detect injection attempts
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
        r"(--|;|'|\")",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]
    
    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """Validate email format."""
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def is_valid_uuid(cls, uuid_str: str) -> bool:
        """Validate UUID format."""
        return bool(cls.UUID_PATTERN.match(uuid_str))
    
    @classmethod
    def detect_sql_injection(cls, text: str) -> bool:
        """Detect potential SQL injection attempts."""
        text_upper = text.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def detect_xss(cls, text: str) -> bool:
        """Detect potential XSS attempts."""
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 10000) -> str:
        """Sanitize text input by removing dangerous characters."""
        if not text:
            return ""
        
        # Truncate to max length
        text = text[:max_length]
        
        # Remove null bytes
        text = text.replace("\x00", "")
        
        # Remove control characters (except newlines and tabs)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        
        return text.strip()
    
    @classmethod
    def validate_question(cls, question: str) -> tuple[bool, str]:
        """Validate a user question for safety."""
        if not question or not question.strip():
            return False, "Question cannot be empty"
        
        if len(question) > 1000:
            return False, "Question too long (max 1000 characters)"
        
        if cls.detect_sql_injection(question):
            logger.warning(f"SQL injection attempt detected: {question[:100]}")
            return False, "Invalid characters in question"
        
        if cls.detect_xss(question):
            logger.warning(f"XSS attempt detected: {question[:100]}")
            return False, "Invalid characters in question"
        
        return True, ""


# ============================================================================
# Password Validation
# ============================================================================

class PasswordValidator:
    """Validate password strength."""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    
    @classmethod
    def validate(cls, password: str) -> tuple[bool, list[str]]:
        """
        Validate password strength.
        Returns (is_valid, list of error messages).
        """
        errors = []
        
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must be at most {cls.MAX_LENGTH} characters")
        
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")
        
        # Check for common weak passwords
        weak_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if password.lower() in weak_passwords:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_strength(cls, password: str) -> str:
        """Get password strength rating."""
        score = 0
        
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if re.search(r"[a-z]", password):
            score += 1
        if re.search(r"[A-Z]", password):
            score += 1
        if re.search(r"\d", password):
            score += 1
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 1
        
        if score <= 2:
            return "weak"
        elif score <= 4:
            return "medium"
        else:
            return "strong"


# ============================================================================
# JWT Token Utilities
# ============================================================================

class TokenBlacklist:
    """Simple in-memory token blacklist for logout functionality."""
    
    def __init__(self):
        self.blacklist: dict[str, float] = {}  # token_hash -> expiry timestamp
    
    def add(self, token: str, expires_at: float):
        """Add a token to the blacklist."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.blacklist[token_hash] = expires_at
        self._cleanup()
    
    def is_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in self.blacklist:
            if time.time() < self.blacklist[token_hash]:
                return True
            else:
                del self.blacklist[token_hash]
        return False
    
    def _cleanup(self):
        """Remove expired tokens from blacklist."""
        now = time.time()
        self.blacklist = {k: v for k, v in self.blacklist.items() if v > now}


# Global token blacklist
token_blacklist = TokenBlacklist()
