import os
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

security = HTTPBearer(auto_error=not DEBUG)


def create_access_token(user_id: int) -> str:
    """Create a JWT token for the given user ID."""
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> int:
    """FastAPI dependency: extract and validate JWT, return authenticated user_id.

    When DEBUG=true, authentication is skipped and the default user ID 1 is returned.
    Otherwise, raises 401 if the token is missing, expired, or invalid.
    """
    if DEBUG:
        # Try to extract user_id from token if provided, otherwise return default
        if credentials is not None:
            try:
                payload = jwt.decode(
                    credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
                )
                user_id_str: str | None = payload.get("sub")
                if user_id_str is not None:
                    return int(user_id_str)
            except JWTError:
                pass
        return 1  # default debug user

    token = credentials.credentials  # type: ignore[union-attr]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return int(user_id_str)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
