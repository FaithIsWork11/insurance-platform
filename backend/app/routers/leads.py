from fastapi import APIRouter, status, Depends, Query, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy import select, func

from app.core.security import require_role
from app.core.app_error import AppError
from app.core.response import ok, paged
from app.db import get_db
from app.models.lead import Lead
from app.schemas.leads import LeadOut

def lead_dump(lead):
    data = LeadOut.model_validate(lead).model_dump()
    data["id"] = str(data["id"])   # ✅ force to string
    return data



router = APIRouter(prefix="/leads", tags=["leads"])


# -----------------------------
# Schemas
# -----------------------------
class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[EmailStr] = None
    zip_code: str
    state: Optional[str] = None
    coverage_type: Optional[str] = None
    source: Optional[str] = None


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    # Only manager/admin will be allowed to set this
    assigned_to: Optional[str] = None


class AssignLeadRequest(BaseModel):
    assigned_to: str


class LeadOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: str
    email: Optional[EmailStr] = None
    zip_code: str
    state: Optional[str] = None
    coverage_type: Optional[str] = None
    source: Optional[str] = None
    status: str
    assigned_to: Optional[str] = None
    updated_at: datetime
    last_contacted_at: Optional[datetime] = None
    created_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def lead_dump(lead: Lead) -> dict:
    return LeadOut.model_validate(lead).model_dump()


def leads_dump(leads: List[Lead]) -> List[dict]:
    return [lead_dump(l) for l in leads]


VALID_STATUSES = {"NEW", "CONTACTED", "QUALIFIED", "TRANSFERRED", "CLOSED"}


# -----------------------------
# Endpoints (RBAC)
# -----------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
def create_lead(
    request: Request,
    payload: LeadCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    lead = Lead(**payload.model_dump())

    # Agents can only create leads assigned to themselves
    if user.get("role") == "agent":
        lead.assigned_to = user.get("sub")

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return ok(data=lead_dump(lead), request=request, meta={"resource": "leads"})


@router.get("")
def list_leads(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    include_deleted: bool = Query(False),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    if include_deleted and user.get("role") != "admin":
        raise AppError(code="LEADS_INCLUDE_DELETED_FORBIDDEN", message="Forbidden", status_code=403)

    offset = (page - 1) * page_size
    base_filter = []

    role = user.get("role")
    sub = user.get("sub")

    # Agents can only see their own assigned leads
    if role == "agent":
        base_filter.append(Lead.assigned_to == sub)

    # Soft delete filter
    if not include_deleted:
        base_filter.append(Lead.is_deleted.is_(False))

    total = db.execute(
        select(func.count()).select_from(Lead).where(*base_filter)
    ).scalar_one()

    leads = (
        db.execute(
            select(Lead)
            .where(*base_filter)
            .order_by(Lead.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return paged(
    items=leads_dump(leads),
    total=total,
    page=page,
    page_size=page_size,
    request=request,
    meta_extra={"include_deleted": include_deleted, "resource": "leads"},
    extra_query={"include_deleted": include_deleted},
)


@router.get("/{lead_id}")
def get_lead(
    request: Request,
    lead_id: str,
    db: Session = Depends(get_db),
    include_deleted: bool = Query(False),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    if include_deleted and user.get("role") != "admin":
        raise AppError(code="LEADS_INCLUDE_DELETED_FORBIDDEN", message="Forbidden", status_code=403)

    lead = db.get(Lead, lead_id)
    if not lead:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    if (not include_deleted) and lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    role = user.get("role")
    sub = user.get("sub")

    if role == "agent" and lead.assigned_to != sub:
        raise AppError(code="LEADS_FORBIDDEN", message="Forbidden", status_code=403)

    return ok(
        data=lead_dump(lead),
        request=request,
        meta={"include_deleted": include_deleted, "resource": "leads"},
    )


@router.delete("/{lead_id}")
def soft_delete_lead(
    request: Request,
    lead_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role({"admin"})),
):
    lead = db.get(Lead, lead_id)
    if not lead or lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    lead.is_deleted = True
    lead.deleted_at = datetime.now(timezone.utc)

    db.add(lead)
    db.commit()

    return ok(
        data={"deleted": True, "soft": True, "lead_id": lead_id},
        request=request,
        meta={"resource": "leads"},
    )


@router.post("/{lead_id}/restore")
def restore_lead(
    request: Request,
    lead_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role({"admin"})),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    lead.is_deleted = False
    lead.deleted_at = None

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return ok(data=lead_dump(lead), request=request, meta={"resource": "leads"})


@router.patch("/{lead_id}")
def update_lead(
    request: Request,
    lead_id: str,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role({"agent", "manager", "admin"})),
):
    lead = db.get(Lead, lead_id)
    if not lead or lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    role = user.get("role")
    sub = user.get("sub")

    # Agent can only update their own assigned leads
    if role == "agent" and lead.assigned_to != sub:
        raise AppError(code="LEADS_FORBIDDEN", message="Forbidden", status_code=403)

    # Agent cannot reassign
    if role == "agent" and payload.assigned_to is not None:
        raise AppError(code="LEADS_FORBIDDEN", message="Forbidden", status_code=403)

    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise AppError(code="LEADS_INVALID_STATUS", message="Invalid status", status_code=400)
        lead.status = payload.status

    if payload.last_contacted_at is not None:
        lead.last_contacted_at = payload.last_contacted_at

    if payload.assigned_to is not None:
        if role not in {"manager", "admin"}:
            raise AppError(code="LEADS_FORBIDDEN", message="Forbidden", status_code=403)
        lead.assigned_to = payload.assigned_to

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return ok(data=lead_dump(lead), request=request, meta={"resource": "leads"})


@router.post("/{lead_id}/assign")
def assign_lead(
    request: Request,
    lead_id: str,
    payload: AssignLeadRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role({"manager", "admin"})),
):
    lead = db.get(Lead, lead_id)
    if not lead or lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    lead.assigned_to = payload.assigned_to

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return ok(data=lead_dump(lead), request=request, meta={"resource": "leads"})