from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.response import ok, paged
from app.core.security import require_role
from app.db import get_db
from app.schemas.leads import AssignLeadRequest, LeadCreate, LeadOut, LeadUpdate
from app.services import leads_service

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_lead(
    request: Request,
    payload: LeadCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    lead = leads_service.create_lead(db=db, payload=payload, user=user, request=request)
    return ok(
        data=LeadOut.model_validate(lead).model_dump(mode="json"),
        request=request,
        meta={"resource": "leads"},
    )


@router.get("", status_code=status.HTTP_200_OK)
def list_leads(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    include_deleted: bool = Query(False),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    items, total = leads_service.list_leads(
        db=db,
        user=user,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )

    return paged(
        items=[LeadOut.model_validate(lead).model_dump(mode="json") for lead in items],
        total=total,
        page=page,
        page_size=page_size,
        request=request,
        meta_extra={"include_deleted": include_deleted, "resource": "leads"},
        extra_query={"include_deleted": include_deleted},
    )


@router.get("/{lead_id}", status_code=status.HTTP_200_OK)
def get_lead(
    request: Request,
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    include_deleted: bool = Query(False),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    lead = leads_service.get_lead(
        db=db,
        lead_id=lead_id,
        user=user,
        include_deleted=include_deleted,
    )
    return ok(
        data=LeadOut.model_validate(lead).model_dump(mode="json"),
        request=request,
        meta={"include_deleted": include_deleted, "resource": "leads"},
    )


@router.patch("/{lead_id}", status_code=status.HTTP_200_OK)
def update_lead(
    request: Request,
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    lead = leads_service.update_lead(
        db=db,
        lead_id=lead_id,
        payload=payload,
        user=user,
        request=request,
    )
    return ok(
        data=LeadOut.model_validate(lead).model_dump(mode="json"),
        request=request,
        meta={"resource": "leads"},
    )


@router.delete("/{lead_id}", status_code=status.HTTP_200_OK)
def soft_delete_lead(
    request: Request,
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_role({"admin"})),
):
    result = leads_service.soft_delete_lead(
        db=db,
        lead_id=lead_id,
        user=user,
        request=request,
    )
    return ok(data=result, request=request, meta={"resource": "leads"})


@router.post("/{lead_id}/restore", status_code=status.HTTP_200_OK)
def restore_lead(
    request: Request,
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_role({"admin"})),
):
    lead = leads_service.restore_lead(
        db=db,
        lead_id=lead_id,
        user=user,
        request=request,
    )
    return ok(
        data=LeadOut.model_validate(lead).model_dump(mode="json"),
        request=request,
        meta={"resource": "leads"},
    )


@router.post("/{lead_id}/assign", status_code=status.HTTP_200_OK)
def assign_lead(
    request: Request,
    lead_id: uuid.UUID,
    payload: AssignLeadRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role({"manager", "admin"})),
):
    lead = leads_service.assign_lead(
        db=db,
        lead_id=lead_id,
        payload=payload,
        user=user,
        request=request,
    )
    return ok(
        data=LeadOut.model_validate(lead).model_dump(mode="json"),
        request=request,
        meta={"resource": "leads"},
    )