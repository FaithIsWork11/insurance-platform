import uuid
from fastapi import APIRouter, Depends, status, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm

from app.db import get_db
from app.models.user import User
from app.schemas.users import UserCreate, UserOut, ALLOWED_ROLES
from app.core.passwords import hash_password, verify_password
from app.core.security import create_access_token
from app.core.audit import audit_event
from app.core.app_error import AppError
from app.core.response import ok

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    role = payload.role.strip().lower()

    if role not in ALLOWED_ROLES:
        raise AppError(
            code="AUTH_INVALID_ROLE",
            message="Invalid role",
            status_code=400,
        )

    # enterprise: self-register agent only
    if role != "agent":
        raise AppError(
            code="AUTH_ROLE_NOT_ALLOWED",
            message="Only agent role can self-register",
            status_code=403,
        )

    existing = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()

    if existing:
        raise AppError(
            code="AUTH_USERNAME_TAKEN",
            message="Username already exists",
            status_code=409,
        )

    if payload.email:
        existing_email = db.execute(
            select(User).where(User.email == str(payload.email))
        ).scalar_one_or_none()

        if existing_email:
            raise AppError(
                code="AUTH_EMAIL_TAKEN",
                message="Email already exists",
                status_code=409,
            )

    user = User(
        username=payload.username,
        email=str(payload.email) if payload.email else None,
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
        request_id=getattr(request.state, "request_id", None),
    )

    db.commit()
    db.refresh(user)

    return ok(
        request=request,
        data=UserOut.model_validate(user).model_dump(),
        meta={"resource": "auth"},
    )


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Enterprise login: accepts BOTH JSON and form data.
    """

    content_type = (request.headers.get("content-type") or "").lower()

    username: str | None = None
    password: str | None = None

    if "application/json" in content_type:
        body = await request.json()
        if isinstance(body, dict):
            username = body.get("username")
            password = body.get("password")
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

    if not username or not password:
        raise AppError(
            code="VALIDATION_ERROR",
            message="username and password are required",
            status_code=422,
            fields={"username": "required", "password": "required"},
        )

    user = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):

        audit_event(
            db,
            action="AUTH_LOGIN_FAILURE",
            entity_type="user",
            request_id=getattr(request.state, "request_id", None),
        )

        db.commit()

        raise AppError(
            code="AUTH_INVALID_CREDENTIALS",
            message="Invalid username or password",
            status_code=401,
        )

    if not user.is_active:
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
        request_id=getattr(request.state, "request_id", None),
    )

    db.commit()

    return ok(
        request=request,
        data={"access_token": access_token, "token_type": "bearer"},
        meta_extra={"resource": "auth"},
        flatten_keys=["access_token", "token_type"],
    )


# OAuth2-compatible token endpoint
@router.post("/token")
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )

    access_token = create_access_token(sub=str(user.id), role=user.role)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }