"""
Authentication module for Finance Tracker

Provides HTTP Basic Authentication for securing API endpoints.
Auth is optional in development but recommended for production.
"""

import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional

from config import settings

security = HTTPBasic(auto_error=False)


def verify_credentials(credentials: Optional[HTTPBasicCredentials]) -> bool:
    """
    Verify HTTP Basic Auth credentials.

    Returns True if:
    - Auth is disabled (no username/password configured)
    - Valid credentials are provided
    """
    # If auth is not configured, allow access (development mode)
    if not settings.AUTH_ENABLED:
        return True

    # Auth is enabled but no credentials provided
    if credentials is None:
        return False

    # Use secrets.compare_digest to prevent timing attacks
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.AUTH_USERNAME.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.AUTH_PASSWORD.encode("utf8")
    )

    return correct_username and correct_password


def require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    """
    FastAPI dependency that requires authentication.

    Usage:
        @app.get("/protected")
        async def protected_route(auth: bool = Depends(require_auth)):
            return {"message": "You are authenticated"}
    """
    if not verify_credentials(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm='Finance Tracker'"},
        )
    return True


def optional_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> bool:
    """
    FastAPI dependency that checks auth but doesn't require it.
    Useful for endpoints that behave differently based on auth status.
    """
    return verify_credentials(credentials)
