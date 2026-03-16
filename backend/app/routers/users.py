from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.response import ok
from app.core.security import require_role
from app.db import get_db
from app.schemas.users import UserCreate, UserOut
from app.services import users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", status_code=201)
def admin_create_user(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role({"manager", "admin"})),
):
    user_obj = users_service.create_user(
        db=db,
        payload=payload,
        actor_user=user,
        request=request,
    )
    data = UserOut.model_validate(user_obj).model_dump()
    return ok(request=request, data=data)


@router.get("", dependencies=[Depends(require_role({"admin"}))])
def admin_list_users(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    users = users_service.list_users(
        db=db,
        limit=limit,
        offset=offset,
    )
    data = [UserOut.model_validate(u).model_dump() for u in users]
    return ok(
        request=request,
        data={"items": data},
        meta_extra={"resource": "users", "limit": limit, "offset": offset},
    )


@router.get("/{user_id}", dependencies=[Depends(require_role({"admin"}))])
def admin_get_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
):
    user_obj = users_service.get_user_by_id(db=db, user_id=user_id)
    return ok(request=request, data=UserOut.model_validate(user_obj).model_dump())


@router.patch("/{user_id}/disable")
def admin_disable_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role({"admin"})),
):
    user_obj = users_service.disable_user(
        db=db,
        user_id=user_id,
        actor_user=user,
        request=request,
    )
    return ok(request=request, data=UserOut.model_validate(user_obj).model_dump())


@router.patch("/{user_id}/enable")
def admin_enable_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role({"admin"})),
):
    user_obj = users_service.enable_user(
        db=db,
        user_id=user_id,
        actor_user=user,
        request=request,
    )
    return ok(request=request, data=UserOut.model_validate(user_obj).model_dump())