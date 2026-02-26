from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.security import require_role
from app.core.app_error import AppError
from app.core.passwords import hash_password
from app.core.response import ok
from app.models.user import User
from app.schemas.users import UserCreate, UserOut, ALLOWED_ROLES

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", status_code=201)
def admin_create_user(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role({"manager", "admin"})),
):
    actor_role = user.get("role")

    # Managers can only create agents
    if actor_role == "manager" and payload.role != "agent":
        raise AppError(
            code="USERS_FORBIDDEN",
            message="Managers can only create agents",
            status_code=403,
        )

    role = payload.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise AppError(code="INVALID_ROLE", message="Invalid role", status_code=400)

    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise AppError(code="USERNAME_EXISTS", message="Username already exists", status_code=400)

    if payload.email is not None:
        existing_email = db.query(User).filter(User.email == str(payload.email)).first()
        if existing_email:
            raise AppError(code="EMAIL_EXISTS", message="Email already exists", status_code=400)

    # ✅ ENTERPRISE: DO NOT set id manually. Let ORM/DB generate UUID.
    user_obj = User(
        username=payload.username,
        email=str(payload.email) if payload.email is not None else None,
        password_hash=hash_password(payload.password),
        role=role,
        is_active=True,
    )

    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)

    # Pydantic -> dict (UUID stays UUID), ok() encodes via jsonable_encoder (UUID safe)
    data = UserOut.model_validate(user_obj).model_dump()
    return ok(request=request, data=data)


@router.get("", dependencies=[Depends(require_role({"admin"}))])
def admin_list_users(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    data = [UserOut.model_validate(u).model_dump() for u in users]
    return ok(
        request=request,
        data={"items": data},
        meta_extra={"resource": "users", "limit": limit, "offset": offset},
    )


@router.get("/{user_id}", dependencies=[Depends(require_role({"admin"}))])
def admin_get_user(request: Request, user_id: str, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise AppError(code="USER_NOT_FOUND", message="User not found", status_code=404)

    return ok(request=request, data=UserOut.model_validate(u).model_dump())


@router.patch("/{user_id}/disable", dependencies=[Depends(require_role({"admin"}))])
def admin_disable_user(request: Request, user_id: str, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise AppError(code="USER_NOT_FOUND", message="User not found", status_code=404)

    u.is_active = False
    db.commit()
    db.refresh(u)

    return ok(request=request, data=UserOut.model_validate(u).model_dump())


@router.patch("/{user_id}/enable", dependencies=[Depends(require_role({"admin"}))])
def admin_enable_user(request: Request, user_id: str, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise AppError(code="USER_NOT_FOUND", message="User not found", status_code=404)

    u.is_active = True
    db.commit()
    db.refresh(u)

    return ok(request=request, data=UserOut.model_validate(u).model_dump())