"""
Pydantic schemas for Case API.
"""
from typing import Optional, List
from datetime import datetime, date, time
from uuid import UUID
from pydantic import BaseModel, Field


class CaseBase(BaseModel):
    """Base schema for Case with common fields."""
    case_number: str
    patient_name: str
    exam_type: str
    exam_date: Optional[date] = None
    exam_time: Optional[time] = None
    exam_location: Optional[str] = None
    referring_party: Optional[str] = None
    referring_email: Optional[str] = None
    report_due_date: Optional[date] = None
    status: Optional[str] = "pending"
    extraction_confidence: Optional[float] = None
    notes: Optional[str] = None


class CaseCreate(CaseBase):
    """Schema for creating a new case."""
    pass


class CaseUpdate(BaseModel):
    """Schema for updating an existing case (all fields optional)."""
    patient_name: Optional[str] = None
    exam_type: Optional[str] = None
    exam_date: Optional[date] = None
    exam_time: Optional[time] = None
    exam_location: Optional[str] = None
    referring_party: Optional[str] = None
    referring_email: Optional[str] = None
    report_due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AttachmentResponse(BaseModel):
    """Schema for attachment in case response."""
    id: UUID
    filename: str
    content_type: Optional[str]
    category: str
    category_reason: Optional[str]
    content_preview: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    storage_provider: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CaseResponse(CaseBase):
    """Schema for case response with full details."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    attachments: List[AttachmentResponse] = []
    emails: List["EmailResponse"] = []

    class Config:
        from_attributes = True


# Import here to avoid circular dependency
from .email import EmailResponse
CaseResponse.model_rebuild()
