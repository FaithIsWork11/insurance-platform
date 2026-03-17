from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.users import UserCreate, UserOut
from app.core.response import ok
from app.schemas.auth import LoginRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
):

    user = auth_service.register_user(
        db=db,
        payload=payload,
        request=request,
    )

    return ok(
        request=request,
        data=UserOut.model_validate(user).model_dump(),
        meta={"resource": "auth"},
    )


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):

    access_token, user = auth_service.login_user(
        db=db,
        username=payload.username,
        password=payload.password,
        request=request,
    )

    return ok(
        request=request,
        data={"access_token": access_token, "token_type": "bearer"},
        meta_extra={"resource": "auth"},
        flatten_keys=["access_token", "token_type"],
    )