from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.app_error import AppError
from app.core.audit import audit_event
from app.core.passwords import hash_password
from app.models.user import User
from app.schemas.users import UserCreate, ALLOWED_ROLES


def create_user(db: Session, payload: UserCreate, actor_user: dict, request) -> User:
    actor_role = actor_user.get("role")

    if actor_role == "manager" and payload.role != "agent":
        raise AppError(
            code="USERS_FORBIDDEN",
            message="Managers can only create agents",
            status_code=403,
        )

    role = payload.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise AppError(
            code="INVALID_ROLE",
            message="Invalid role",
            status_code=400,
        )

    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise AppError(
            code="USERNAME_EXISTS",
            message="Username already exists",
            status_code=400,
        )

    if payload.email is not None:
        existing_email = db.query(User).filter(User.email == str(payload.email)).first()
        if existing_email:
            raise AppError(
                code="EMAIL_EXISTS",
                message="Email already exists",
                status_code=400,
            )

    user_obj = User(
        username=payload.username,
        email=str(payload.email) if payload.email is not None else None,
        password_hash=hash_password(payload.password),
        role=role,
        is_active=True,
    )

    db.add(user_obj)
    db.flush()

    audit_event(
        db,
        actor_user_id=actor_user.get("sub_uuid") or actor_user.get("sub"),
        action="USERS_CREATE",
        entity_type="user",
        entity_id=str(user_obj.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={
            "created_username": user_obj.username,
            "created_role": user_obj.role,
            "created_email": user_obj.email,
        },
    )

    db.commit()
    db.refresh(user_obj)
    return user_obj


def list_users(db: Session, limit: int = 50, offset: int = 0) -> list[User]:
    users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return users


def get_user_by_id(db: Session, user_id: str) -> User:
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        raise AppError(
            code="USER_NOT_FOUND",
            message="User not found",
            status_code=404,
        )
    return user_obj


def disable_user(db: Session, user_id: str, actor_user: dict, request) -> User:
    user_obj = get_user_by_id(db, user_id)

    user_obj.is_active = False

    audit_event(
        db,
        actor_user_id=actor_user.get("sub_uuid") or actor_user.get("sub"),
        action="USERS_DISABLE",
        entity_type="user",
        entity_id=str(user_obj.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={
            "is_active": user_obj.is_active,
        },
    )

    db.commit()
    db.refresh(user_obj)
    return user_obj


def enable_user(db: Session, user_id: str, actor_user: dict, request) -> User:
    user_obj = get_user_by_id(db, user_id)

    user_obj.is_active = True

    audit_event(
        db,
        actor_user_id=actor_user.get("sub_uuid") or actor_user.get("sub"),
        action="USERS_ENABLE",
        entity_type="user",
        entity_id=str(user_obj.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={
            "is_active": user_obj.is_active,
        },
    )

    db.commit()
    db.refresh(user_obj)
    return user_obj