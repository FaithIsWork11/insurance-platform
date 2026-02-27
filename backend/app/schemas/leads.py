from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


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
    assigned_to: Optional[str] = None  # manager/admin only (enforced in router)


class AssignLeadRequest(BaseModel):
    assigned_to: str


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
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
    created_at: datetime
    updated_at: datetime
    last_contacted_at: Optional[datetime] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None