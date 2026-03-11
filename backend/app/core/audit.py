# backend/app/core/audit.py
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def audit_event(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | str | None = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    request_id: Optional[str] = None,
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
    )
    db.add(row)
    db.flush()
    return row