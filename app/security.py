import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt

# In production, set SECRET_KEY in the environment (e.g. `openssl rand -hex 32`).
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-dev-only-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Returns the user id, or raises jwt.PyJWTError if invalid/expired."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return int(payload["sub"])
