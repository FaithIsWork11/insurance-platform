from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.lead import Lead


def get_by_id(db: Session, lead_id: UUID) -> Lead | None:
    return db.get(Lead, lead_id)


def list_with_count(
    db: Session,
    *,
    filters: list,
    offset: int,
    limit: int,
) -> Tuple[List[Lead], int]:
    total = db.execute(
        select(func.count()).select_from(Lead).where(*filters)
    ).scalar_one()

    leads = (
        db.execute(
            select(Lead)
            .where(*filters)
            .order_by(Lead.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return leads, total


def create(db: Session, lead: Lead) -> Lead:
    db.add(lead)
    db.flush()
    return lead


def update(db: Session, lead: Lead) -> Lead:
    db.add(lead)
    db.flush()
    return lead


def soft_delete(db: Session, lead: Lead) -> Lead:
    lead.is_deleted = True
    lead.deleted_at = datetime.now(timezone.utc)
    lead.updated_at = datetime.now(timezone.utc)

    db.add(lead)
    db.flush()
    return lead


def restore(db: Session, lead: Lead) -> Lead:
    lead.is_deleted = False
    lead.deleted_at = None
    lead.updated_at = datetime.now(timezone.utc)

    db.add(lead)
    db.flush()
    return lead


def refresh(db: Session, lead: Lead) -> Lead:
    db.refresh(lead)
    return lead