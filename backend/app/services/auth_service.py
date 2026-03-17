from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_error import AppError
from app.core.audit import audit_event
from app.core.passwords import hash_password, verify_password
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.users import ALLOWED_ROLES, UserCreate


def register_user(db: Session, payload: UserCreate, request) -> User:
    request_id = getattr(request.state, "request_id", None)

    username = payload.username.strip()
    role = payload.role.strip().lower()
    email = str(payload.email).strip().lower() if payload.email else None

    if role not in ALLOWED_ROLES:
        raise AppError(
            code="AUTH_INVALID_ROLE",
            message="Invalid role",
            status_code=400,
        )

    if role != "agent":
        raise AppError(
            code="AUTH_ROLE_NOT_ALLOWED",
            message="Only agent role can self-register",
            status_code=403,
        )

    existing = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()

    if existing:
        raise AppError(
            code="AUTH_USERNAME_TAKEN",
            message="Username already exists",
            status_code=409,
        )

    if email:
        existing_email = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing_email:
            raise AppError(
                code="AUTH_EMAIL_TAKEN",
                message="Email already exists",
                status_code=409,
            )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        role=role,
        is_active=True,
    )

    db.add(user)
    db.flush()

    audit_event(
        db,
        actor_user_id=user.id,
        action="AUTH_REGISTER_SUCCESS",
        entity_type="user",
        entity_id=str(user.id),
        request_id=request_id,
    )

    db.commit()
    db.refresh(user)

    return user


def login_user(db: Session, username: str, password: str, request) -> tuple[str, User]:
    request_id = getattr(request.state, "request_id", None)
    username = username.strip()

    user = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        audit_event(
            db,
            action="AUTH_LOGIN_FAILURE",
            entity_type="user",
            request_id=request_id,
            metadata_json={"username": username},
        )
        db.commit()

        raise AppError(
            code="AUTH_INVALID_CREDENTIALS",
            message="Invalid username or password",
            status_code=401,
        )

    if not user.is_active:
        audit_event(
            db,
            actor_user_id=user.id,
            action="AUTH_LOGIN_DISABLED",
            entity_type="user",
            entity_id=str(user.id),
            request_id=request_id,
        )
        db.commit()

        raise AppError(
            code="AUTH_USER_DISABLED",
            message="User is disabled",
            status_code=403,
        )

    access_token = create_access_token(sub=str(user.id), role=user.role)

    audit_event(
        db,
        actor_user_id=user.id,
        action="AUTH_LOGIN_SUCCESS",
        entity_type="user",
        entity_id=str(user.id),
        request_id=request_id,
    )

    db.commit()

    return access_token, user