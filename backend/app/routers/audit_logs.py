from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.response import ok, paged
from app.core.security import require_role
from app.db import get_db
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def audit_log_dump(log: AuditLog) -> dict:
    return {
        "id": str(log.id),
        "actor_user_id": str(log.actor_user_id) if log.actor_user_id else None,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "request_id": log.request_id,
        "metadata_json": log.metadata_json,
        "ip_address": log.ip_address,
        "endpoint_path": log.endpoint_path,
        "http_method": log.http_method,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("", status_code=status.HTTP_200_OK)
def list_audit_logs(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_user_id: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    user=Depends(require_role({"admin"})),
):
    filters = []

    if action:
        filters.append(AuditLog.action == action)

    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)

    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)

    if actor_user_id:
        filters.append(AuditLog.actor_user_id == actor_user_id)

    if request_id:
        filters.append(AuditLog.request_id == request_id)

    if date_from:
        filters.append(AuditLog.created_at >= date_from)

    if date_to:
        filters.append(AuditLog.created_at <= date_to)

    offset = (page - 1) * page_size

    total = db.execute(
        select(func.count()).select_from(AuditLog).where(*filters)
    ).scalar_one()

    logs = (
        db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return paged(
        items=[audit_log_dump(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        request=request,
        meta_extra={"resource": "audit_logs"},
        extra_query={
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_user_id": actor_user_id,
            "request_id": request_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
    )