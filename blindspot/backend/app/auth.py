"""Password hashing and JWT helpers."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(plain: str) -> str:
    # bcrypt has a 72-byte hard limit; we truncate explicitly so longer
    # passphrases hash deterministically rather than erroring.
    hashed = bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


def create_access_token(*, subject: str, extra: dict | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    settings = get_settings()
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exc
        user_id = int(user_id_str)
    except (JWTError, ValueError) as exc:
        raise credentials_exc from exc

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exc
    return user
