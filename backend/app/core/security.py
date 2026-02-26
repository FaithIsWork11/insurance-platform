import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.core.app_error import AppError

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def create_access_token(sub: Any, role: str) -> str:
    """
    Enterprise rule:
    - JWT claims must be JSON-serializable.
    - Always store 'sub' as a STRING.
    """
    if isinstance(sub, uuid.UUID):
        sub = str(sub)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=EXPIRE_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def require_role(allowed: set[str]):
    def _dep(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
    ):
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        except JWTError:
            raise AppError(code="AUTH_UNAUTHORIZED", message="Unauthorized", status_code=401)

        role = data.get("role")
        if role not in allowed:
            raise AppError(code="AUTH_FORBIDDEN", message="Forbidden", status_code=403)

        sub = data.get("sub")
        if not sub:
            raise AppError(code="AUTH_UNAUTHORIZED", message="Unauthorized", status_code=401)

        # ✅ Enterprise: User.id is UUID, so validate/cast sub -> UUID
        try:
            sub_uuid = uuid.UUID(str(sub))
        except ValueError:
            raise AppError(code="AUTH_UNAUTHORIZED", message="Unauthorized", status_code=401)

        # ✅ Enforce user exists + is_active
        user = db.query(User).filter(User.id == sub_uuid).first()
        if not user:
            raise AppError(code="AUTH_UNAUTHORIZED", message="Unauthorized", status_code=401)

        if not user.is_active:
            raise AppError(code="AUTH_DISABLED", message="User is disabled", status_code=403)

        # Return claims (keep sub as string in token), but we also attach parsed uuid for internal use
        data["sub_uuid"] = str(sub_uuid)
        return data

    return _dep