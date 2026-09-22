"""
Auth dependencies for FastAPI route protection.

Usage:
    @router.get("/me")
    def get_me(current_user: Users = Depends(get_current_user)):
        return current_user
"""

import uuid

import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.config.database import get_db
from app.config.settings import settings
from app.models.user import Users

# This tells Swagger UI where to obtain a token (the login endpoint)
oauth2_scheme = HTTPBearer()

KEY = settings.secret_key
ALGO = settings.algorithm

logger = structlog.get_logger()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Users:
    """
    Extract the user from the Authorization: Bearer <access_token> header.
    This is the dependency you inject into any protected route.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # .credentials is the raw JWT string; `credentials` itself is an
        # HTTPAuthorizationCredentials object — passing the whole object to
        # jwt.decode() caused the 401 error.
        payload = decode_token(credentials.credentials, KEY, ALGO)

        # Ensure this is an access token, not a refresh token
        if payload.get("type") != "access":
            logger.warning("auth_failed", reason="wrong_token_type", token_type=payload.get("type"))
            raise credentials_exception

        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            logger.warning("auth_failed", reason="missing_sub_claim")
            raise credentials_exception

        user_id = uuid.UUID(user_id_str)

    except jwt.ExpiredSignatureError:
        logger.warning("auth_failed", reason="token_expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError) as exc:
        logger.warning("auth_failed", reason="invalid_token", error=str(exc))
        raise credentials_exception

    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        logger.warning("auth_failed", reason="user_not_found", user_id=str(user_id))
        raise credentials_exception

    return user
