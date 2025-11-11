"""
Authentication middleware and utilities
"""
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import warnings

security = HTTPBearer()

# In-memory token storage (for simplicity; use Redis or DB in production)
_active_tokens = {}

def get_admin_password() -> str:
    """
    Get admin password from environment.

    WARNING: The default password is for DEVELOPMENT ONLY!
    ALWAYS set ADMIN_PASSWORD environment variable in production.
    """
    # Default password for development - NOT for production use!
    default_dev_password = "cbf2025admin"
    password = os.getenv("ADMIN_PASSWORD")
    
    if not password:
        # Using default password - log warning
        warnings.warn(
            "⚠️  Using default admin password! Set ADMIN_PASSWORD environment variable in production.",
            UserWarning,
            stacklevel=2
        )
        password = default_dev_password
    
    return password


def generate_token() -> str:
    """Generate a secure random token"""
    token = secrets.token_urlsafe(32)
    # Store token with expiration (24 hours)
    _active_tokens[token] = datetime.now() + timedelta(hours=24)
    return token


def verify_token(token: str) -> bool:
    """Verify if token is valid and not expired"""
    if token not in _active_tokens:
        return False

    expiration = _active_tokens[token]
    if datetime.now() > expiration:
        # Token expired, remove it
        del _active_tokens[token]
        return False

    return True


def verify_admin_password(password: str) -> bool:
    """Verify admin password"""
    expected = get_admin_password()
    return secrets.compare_digest(password, expected)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Dependency to verify JWT token"""
    token = credentials.credentials

    if not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


def cleanup_expired_tokens():
    """Remove expired tokens from storage"""
    now = datetime.now()
    expired = [token for token, exp in _active_tokens.items() if now > exp]
    for token in expired:
        del _active_tokens[token]
