from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def build_audit_context(request: Request) -> dict[str, Optional[str]]:
    """
    Build common request context fields for audit logging.
    """
    return {
        "request_id": getattr(request.state, "request_id", None),
        "ip_address": getattr(request.client, "host", None) if request.client else None,
        "endpoint_path": str(request.url.path),
        "http_method": request.method,
    }


def audit_event(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | str | None = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata_json: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    http_method: Optional[str] = None,
) -> AuditLog:
    """
    Add an audit log row to the current SQLAlchemy session.

    This helper does NOT commit.
    The caller controls transaction boundaries.
    """
    actor_uuid: uuid.UUID | None = None
    if actor_user_id is not None:
        actor_uuid = (
            actor_user_id
            if isinstance(actor_user_id, uuid.UUID)
            else uuid.UUID(str(actor_user_id))
        )

    row = AuditLog(
        actor_user_id=actor_uuid,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        metadata_json=metadata_json,
        ip_address=ip_address,
        endpoint_path=endpoint_path,
        http_method=http_method,
    )

    db.add(row)
    db.flush()
    return row