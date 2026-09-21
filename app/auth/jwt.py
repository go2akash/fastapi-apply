import jwt
from datetime import datetime, timedelta, timezone

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict, KEY: str, ALGO: str) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, KEY, ALGO)


def create_refresh_token(data: dict, KEY: str, ALGO: str) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, KEY, ALGO)


def decode_token(token: str, KEY: str, ALGO: str) -> dict:
    """Decode and verify a JWT token. Raises jwt.exceptions on failure."""
    return jwt.decode(token, KEY, algorithms=[ALGO])
