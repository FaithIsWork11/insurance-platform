from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.app_error import AppError
from app.core.audit import audit_event
from app.models.lead import Lead
from app.models.user import User
from app.schemas.leads import AssignLeadRequest, LeadCreate, LeadUpdate

VALID_STATUSES = {"NEW", "CONTACTED", "QUALIFIED", "TRANSFERRED", "CLOSED"}
ALLOWED_ASSIGNEE_ROLES = {"agent", "manager"}


def _normalize_uuid_value(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        raise AppError(
            code="LEADS_INVALID_ASSIGNEE",
            message="assigned_to_user_id must be a valid UUID",
            status_code=400,
        )


def _get_valid_assignee(db: Session, assigned_to_user_id: str | UUID | None) -> User | None:
    normalized = _normalize_uuid_value(assigned_to_user_id)
    if normalized is None:
        return None

    assignee = db.execute(
        select(User).where(User.id == normalized)
    ).scalar_one_or_none()

    if not assignee:
        raise AppError(
            code="LEADS_ASSIGNEE_NOT_FOUND",
            message="Assigned user does not exist",
            status_code=404,
        )

    if not assignee.is_active:
        raise AppError(
            code="LEADS_ASSIGNEE_INACTIVE",
            message="Assigned user is inactive",
            status_code=400,
        )

    role = (assignee.role or "").strip().lower()
    if role not in ALLOWED_ASSIGNEE_ROLES:
        raise AppError(
            code="LEADS_ASSIGNEE_INVALID_ROLE",
            message="Lead can only be assigned to an agent or manager",
            status_code=400,
        )

    return assignee


def _require_lead_access(user: dict, lead: Lead) -> None:
    role = user.get("role")
    sub = user.get("sub")

    if role == "agent":
        if lead.assigned_to_user_id is None or str(lead.assigned_to_user_id) != str(sub):
            raise AppError(
                code="LEADS_FORBIDDEN",
                message="Forbidden",
                status_code=403,
            )


def create_lead(db: Session, payload: LeadCreate, user: dict, request) -> Lead:
    lead = Lead(**payload.model_dump())

    if user.get("role") == "agent":
        user_uuid = _normalize_uuid_value(user.get("sub"))
        lead.assigned_to_user_id = user_uuid

    db.add(lead)
    db.flush()

    audit_event(
        db,
        actor_user_id=user.get("sub_uuid") or user.get("sub"),
        action="LEADS_CREATE",
        entity_type="lead",
        entity_id=str(lead.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={
            "assigned_to_user_id": str(lead.assigned_to_user_id) if lead.assigned_to_user_id else None,
            "status": lead.status,
        },
    )

    db.commit()
    db.refresh(lead)
    return lead


def list_leads(
    db: Session,
    user: dict,
    page: int,
    page_size: int,
    include_deleted: bool,
) -> tuple[List[Lead], int]:

    if include_deleted and user.get("role") != "admin":
        raise AppError(
            code="LEADS_INCLUDE_DELETED_FORBIDDEN",
            message="Forbidden",
            status_code=403,
        )

    offset = (page - 1) * page_size
    base_filter = []

    role = user.get("role")
    sub = user.get("sub")

    if role == "agent":
        user_uuid = _normalize_uuid_value(sub)
        base_filter.append(Lead.assigned_to_user_id == user_uuid)

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

    return leads, total


def get_lead(db: Session, lead_id: UUID, user: dict, include_deleted: bool) -> Lead:

    if include_deleted and user.get("role") != "admin":
        raise AppError(
            code="LEADS_INCLUDE_DELETED_FORBIDDEN",
            message="Forbidden",
            status_code=403,
        )

    lead = db.get(Lead, lead_id)

    if not lead:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    if (not include_deleted) and lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    _require_lead_access(user, lead)

    return lead


def update_lead(db: Session, lead_id: UUID, payload: LeadUpdate, user: dict, request) -> Lead:

    lead = db.get(Lead, lead_id)

    if not lead or lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    _require_lead_access(user, lead)

    role = user.get("role")

    if payload.status is not None and payload.status not in VALID_STATUSES:
        raise AppError(
            code="LEADS_INVALID_STATUS",
            message="Invalid status",
            status_code=400,
        )

    old_status = lead.status
    old_assigned_to_user_id = lead.assigned_to_user_id

    if payload.status is not None:
        lead.status = payload.status

    if payload.last_contacted_at is not None:
        lead.last_contacted_at = payload.last_contacted_at

    if payload.assigned_to_user_id is not None:

        if role not in {"manager", "admin"}:
            raise AppError(
                code="LEADS_FORBIDDEN",
                message="Forbidden",
                status_code=403,
            )

        assignee = _get_valid_assignee(db, payload.assigned_to_user_id)
        lead.assigned_to_user_id = assignee.id

    lead.updated_at = datetime.now(timezone.utc)
    db.add(lead)

    audit_event(
        db,
        actor_user_id=user.get("sub_uuid") or user.get("sub"),
        action="LEADS_UPDATE",
        entity_type="lead",
        entity_id=str(lead.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={
            "old_status": old_status,
            "new_status": lead.status,
            "old_assigned_to_user_id": str(old_assigned_to_user_id) if old_assigned_to_user_id else None,
            "new_assigned_to_user_id": str(lead.assigned_to_user_id) if lead.assigned_to_user_id else None,
        },
    )

    db.commit()
    db.refresh(lead)

    return lead


def soft_delete_lead(db: Session, lead_id: UUID, user: dict, request) -> dict:

    lead = db.get(Lead, lead_id)

    if not lead or lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    lead.is_deleted = True
    lead.deleted_at = datetime.now(timezone.utc)
    lead.updated_at = datetime.now(timezone.utc)

    db.add(lead)

    audit_event(
        db,
        actor_user_id=user.get("sub_uuid") or user.get("sub"),
        action="LEADS_SOFT_DELETE",
        entity_type="lead",
        entity_id=str(lead.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={"deleted": True},
    )

    db.commit()

    return {"deleted": True, "soft": True, "lead_id": str(lead_id)}


def restore_lead(db: Session, lead_id: UUID, user: dict, request) -> Lead:

    lead = db.get(Lead, lead_id)

    if not lead:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    lead.is_deleted = False
    lead.deleted_at = None
    lead.updated_at = datetime.now(timezone.utc)

    db.add(lead)

    audit_event(
        db,
        actor_user_id=user.get("sub_uuid") or user.get("sub"),
        action="LEADS_RESTORE",
        entity_type="lead",
        entity_id=str(lead.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={"restored": True},
    )

    db.commit()
    db.refresh(lead)

    return lead


def assign_lead(db: Session, lead_id: UUID, payload: AssignLeadRequest, user: dict, request) -> Lead:

    lead = db.get(Lead, lead_id)

    if not lead or lead.is_deleted:
        raise AppError(code="LEAD_NOT_FOUND", message="Lead not found", status_code=404)

    assignee = _get_valid_assignee(db, payload.assigned_to_user_id)

    old_assigned_to_user_id = lead.assigned_to_user_id
    old_status = lead.status

    lead.assigned_to_user_id = assignee.id
    lead.updated_at = datetime.now(timezone.utc)

    db.add(lead)

    audit_event(
        db,
        actor_user_id=user.get("sub_uuid") or user.get("sub"),
        action="LEADS_ASSIGN",
        entity_type="lead",
        entity_id=str(lead.id),
        request_id=getattr(request.state, "request_id", None),
        metadata_json={
            "old_assigned_to_user_id": str(old_assigned_to_user_id) if old_assigned_to_user_id else None,
            "new_assigned_to_user_id": str(lead.assigned_to_user_id) if lead.assigned_to_user_id else None,
            "old_status": old_status,
            "new_status": lead.status,
            "assignee_role": assignee.role,
            "assignee_username": assignee.username,
        },
    )

    db.commit()
    db.refresh(lead)

    return lead