"""
User service — pure business logic. ZERO HTTP imports.

WHY A SERVICE LAYER?
---------------------
Your original user.py endpoint did EVERYTHING in one function:
  1. Check duplicate email (DB query)
  2. Hash password
  3. Create ORM object & commit (DB write)
  4. Create JWT tokens
  5. Set cookies (HTTP concern)

Problems with that approach:
- Can't unit test "create user" without spinning up HTTP + DB
- Can't reuse "create user" from a CLI command or background task
- Every endpoint becomes a God function as features grow

The service layer extracts steps 1-4 into pure functions.
The router ONLY does step 5 (HTTP concerns: cookies, status codes, headers).

FIRST-PRINCIPLES RULE:
  A service function receives typed data, performs business logic,
  and returns typed data or raises a domain exception.
  It NEVER imports anything from fastapi, starlette, or any HTTP library.

This is the SAME pattern in every language:
- Go: A struct with methods that accept context.Context + domain types
- Java: A @Service class injected into @Controllers
- Node: A plain class/module imported by Express route handlers

WHY CLASSES HERE (vs your original functions)?
-----------------------------------------------
A class is just a closure that holds an expensive resource handle.
UserService.__init__(self, db) stores the database session pointer.
Every method reuses that same session without re-creating it.

You could do the exact same thing with closures:
    def make_user_service(db):
        def register(payload): ...
        def login(payload): ...
        return register, login

Classes are just the conventional way to group related functions
that share the same resource. The physical effect is identical.
"""

import structlog
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, create_refresh_token
from app.config.settings import settings
from app.models.user import Users
from app.schemas.security import LoginRequest
from app.schemas.user import UserCreate
from app.services import DuplicateEmailError, InvalidCredentialsError
from app.utils.security import get_password_hash, verify_password

logger = structlog.get_logger()

KEY = settings.secret_key
ALGO = settings.algorithm


class UserService:
    """
    Handles user-related business operations.

    This class knows about:     Users, passwords, tokens, database
    This class knows NOTHING about:  HTTP, cookies, status codes, Request/Response
    """

    def __init__(self, db: Session):
        # The db session is an expensive resource handle.
        # Created once per request by FastAPI's Depends(get_db),
        # then passed here. NOT created inside the service.
        self.db = db

    def register(self, payload: UserCreate) -> dict:
        """
        Register a new user. Returns access + refresh tokens.

        Raises:
            DuplicateEmailError: if email is already taken
        """
        logger.info("user_registration_started", email=payload.email)

        # ── Business rule: no duplicate emails ──
        existing = self.db.query(Users).filter(Users.email == payload.email).first()
        if existing:
            logger.warning("user_registration_duplicate_email", email=payload.email)
            raise DuplicateEmailError(f"Email {payload.email} is already registered")

        # ── Create user ──
        user = Users(
            name=payload.name,
            email=payload.email,
            hash_password=get_password_hash(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info("user_created", user_id=str(user.id), email=user.email)

        # ── Generate tokens ──
        access_token = create_access_token({"sub": str(user.id)}, KEY, ALGO)
        refresh_token = create_refresh_token({"sub": str(user.id)}, KEY, ALGO)

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def login(self, payload: LoginRequest) -> dict:
        """
        Authenticate a user. Returns access + refresh tokens.

        Raises:
            InvalidCredentialsError: if email/password don't match
        """
        logger.info("user_login_attempted", email=payload.email)

        user = self.db.query(Users).filter(Users.email == payload.email).first()
        if not user or not verify_password(payload.password, user.hash_password):
            # SECURITY: Don't log whether email exists or password was wrong.
            # Attackers use that to enumerate valid emails.
            logger.warning("user_login_failed", email=payload.email)
            raise InvalidCredentialsError("Invalid email or password")

        logger.info("user_login_success", user_id=str(user.id))

        access_token = create_access_token({"sub": str(user.id)}, KEY, ALGO)
        refresh_token = create_refresh_token({"sub": str(user.id)}, KEY, ALGO)

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def get_user_by_email(self, email: str) -> Users:
        """Look up a user by email. Raises UserNotFoundError if missing."""
        from app.services import UserNotFoundError

        user = self.db.query(Users).filter(Users.email == email).first()
        if not user:
            logger.warning("user_lookup_not_found", email=email)
            raise UserNotFoundError(f"User with email {email} not found")
        return user
