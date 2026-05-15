"""JWT authentication helpers (ADR-012).

Uses python-jose (HS256) for token encode/decode and bcrypt for password hashing.
JWT_SECRET must be set in env; if absent the app raises at startup so the error
is obvious rather than silently using an insecure default.

Token structure:
  {
    "sub": "<user_id as str>",
    "email": "<email>",
    "is_buyer": bool,
    "is_merchant": bool,
    "exp": <unix timestamp>
  }

Token lifetime: ACCESS_TOKEN_EXPIRE_MINUTES (default 60 min). Refresh tokens
are deferred to post-MVP.

FastAPI dependency:
  from auth import get_current_user
  @app.get("/buyer/me")
  async def me(user: UserPayload = Depends(get_current_user)):
      ...
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

_bearer = HTTPBearer(auto_error=False)


def _get_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET env var is required but not set")
    return secret


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of plain. Work factor 12 is OWASP minimum (2026)."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT encode / decode
# ---------------------------------------------------------------------------

class UserPayload(BaseModel):
    """Decoded JWT claims, injected by get_current_user."""
    user_id: str
    email: str
    is_buyer: bool
    is_merchant: bool


def create_access_token(
    user_id: str,
    email: str,
    is_buyer: bool,
    is_merchant: bool,
) -> str:
    """Mint a signed JWT for the given user."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "email": email,
        "is_buyer": is_buyer,
        "is_merchant": is_merchant,
        # exp claim tells jose to validate expiry automatically on decode.
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(claims, _get_secret(), algorithm=_ALGORITHM)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserPayload:
    """FastAPI dependency — validates Bearer token and returns decoded claims.

    Raises 401 if the token is missing, expired, or tampered with.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            _get_secret(),
            algorithms=[_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return UserPayload(
        user_id=payload["sub"],
        email=payload["email"],
        is_buyer=payload.get("is_buyer", False),
        is_merchant=payload.get("is_merchant", False),
    )
