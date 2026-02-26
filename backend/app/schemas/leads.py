from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field


# --- Enums (optional but recommended) ---
ALLOWED_LEAD_STATUSES = {
    "new",
    "contacted",
    "qualified",
    "unqualified",
    "sold",
    "dead",
}


class LeadCreate(BaseModel):
    # Keep minimal required fields; everything else optional
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

    # workflow fields
    status: str = "new"
    source: Optional[str] = None  # e.g. everquote, webform, fb, manual
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    # All optional for PATCH updates
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None

    # assignment / workflow
    assigned_to_user_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None  # if you use soft delete


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

    status: str
    source: Optional[str] = None
    notes: Optional[str] = None

    # assignment
    assigned_to_user_id: Optional[uuid.UUID] = None

    # soft delete / activity
    is_active: bool

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None