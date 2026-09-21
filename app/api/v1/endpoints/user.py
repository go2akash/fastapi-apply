"""
User endpoints — the TRANSPORT LAYER.

WHAT CHANGED FROM YOUR ORIGINAL:
----------------------------------
Your original user.py was 153 lines doing EVERYTHING:
  DB queries, password hashing, token creation, cookie setting, error handling.

Now it's a thin adapter that does ONLY 3 things:
  1. Receive the validated request (Pydantic handles this automatically)
  2. Call the service layer (which does the actual work)
  3. Map domain exceptions to HTTP status codes

WHY THIS MATTERS:
------------------
- The service layer can be called from a CLI, a background job, or another service
- Unit tests can test business logic WITHOUT spinning up an HTTP server
- Each file has ONE responsibility — easier to read, debug, and modify

THE ROUTER'S ONLY JOB:
  Parse HTTP → Call Service → Map Errors → Serialize Response

This is identical in every framework:
- Go Gin:       func(c *gin.Context) { result, err := svc.Register(input); ... }
- Express:      (req, res) => { try { result = svc.register(req.body) } catch(e) { ... } }
- Java Spring:  @PostMapping → call service → map exceptions via @ControllerAdvice
"""

import os
import uuid

import jwt
import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.jwt import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config.database import get_db
from app.config.settings import settings
from app.models import Users
from app.schemas.security import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead
from app.services import DuplicateEmailError, InvalidCredentialsError, UserNotFoundError
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger()

KEY = settings.secret_key
ALGO = settings.algorithm


# ── Dependency: create a UserService instance per request ──
# This is Dependency Injection via FastAPI's Depends().
# The framework-agnostic concept: pass the DB handle into the service constructor.
# In Go: svc := NewUserService(dbPool) — done once in main().
# In FastAPI: done per-request because each request gets its own DB session.
def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


# ──────────────────────────────────────────────────────────
# SIGNUP — create user, return access token + refresh cookie
# ──────────────────────────────────────────────────────────
@router.post("/create", response_model=TokenResponse, status_code=201)
def create_user(
    user_in: UserCreate,
    response: Response,
    service: UserService = Depends(get_user_service),
):
    """
    Look how clean this is now:
    1. Call service (one line)
    2. Set cookie (HTTP concern — belongs here, not in service)
    3. Return response
    """
    try:
        result = service.register(user_in)
    except DuplicateEmailError:
        raise HTTPException(status_code=400, detail="Email already registered")

    _set_refresh_cookie(response, result["refresh_token"])
    return TokenResponse(access_token=result["access_token"])


# ──────────────────────────────────────────────────────────
# LOGIN — verify credentials, return access token + refresh cookie
# ──────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,       # <-- Now uses LoginRequest, not UserCreate
    response: Response,
    service: UserService = Depends(get_user_service),
):
    try:
        result = service.login(credentials)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Bind user_id to context so all subsequent logs include it
    structlog.contextvars.bind_contextvars(user_id=str(result["user"].id))

    _set_refresh_cookie(response, result["refresh_token"])
    return TokenResponse(access_token=result["access_token"])


# ──────────────────────────────────────────────────────────
# REFRESH — read refresh token from cookie, return new access token
# ──────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = decode_token(refresh_token, KEY, ALGO)

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired, please login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(Users).filter(Users.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    logger.info("token_refreshed", user_id=user_id)

    new_access_token = create_access_token({"sub": str(user.id)}, KEY, ALGO)
    new_refresh_token = create_refresh_token({"sub": str(user.id)}, KEY, ALGO)

    _set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(access_token=new_access_token)


# ──────────────────────────────────────────────────────────
# LOGOUT — clear the refresh cookie
# ──────────────────────────────────────────────────────────
@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(key="refresh_token", httponly=True, path="/")
    logger.info("user_logged_out")
    return None


# ──────────────────────────────────────────────────────────
# PROTECTED ROUTE — requires valid access token
# ──────────────────────────────────────────────────────────
@router.get("/me", response_model=UserRead)
def get_me(current_user: Users = Depends(get_current_user)):
    return current_user


@router.get("/users/", response_model=UserRead)
def get_user(
    user_email: str,
    service: UserService = Depends(get_user_service),
):
    try:
        return service.get_user_by_email(user_email)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


# ──────────────────────────────────────────────────────────
# Helper — set the refresh token cookie with secure defaults
# ──────────────────────────────────────────────────────────
def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    is_production = settings.environment == "production"

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        path="/",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
