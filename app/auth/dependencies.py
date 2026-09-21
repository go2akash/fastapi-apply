"""
Auth dependencies for FastAPI route protection.

Usage:
    @router.get("/me")
    def get_me(current_user: Users = Depends(get_current_user)):
        return current_user
"""

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.config.database import get_db
from app.config.settings import settings
from app.models.user import Users

# This tells Swagger UI where to obtain a token (the login endpoint)
oauth2_scheme = HTTPBearer()

KEY = settings.secret_key
ALGO = settings.algorithm


def get_current_user(
    token: str = Depends(oauth2_scheme),
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
        payload = decode_token(token, KEY, ALGO)

        # Ensure this is an access token, not a refresh token
        if payload.get("type") != "access":
            raise credentials_exception

        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception

        user_id = uuid.UUID(user_id_str)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception

    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user
