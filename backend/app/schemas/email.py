"""
Pydantic schemas for Email API.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class AttachmentData(BaseModel):
    """Schema for attachment data in email ingestion."""
    filename: str
    content_type: Optional[str] = None
    text_content: Optional[str] = None  # For text files
    pdf_images: Optional[List[str]] = None  # Base64-encoded PNG images for PDFs (one per page)


class EmailIngest(BaseModel):
    """Schema for ingesting a new email."""

    subject: str = Field(description="Email subject line")
    sender: str = Field(description="Sender email address")
    recipients: List[str] = Field(description="List of recipient email addresses")
    body: str = Field(description="Email body text")
    attachments: List[AttachmentData] = Field(
        default_factory=list,
        description="List of attachments"
    )
    received_at: Optional[datetime] = Field(
        default=None,
        description="When the email was received (defaults to current time if not provided)"
    )


class EmailResponse(BaseModel):
    """Schema for email response."""

    id: UUID
    case_id: Optional[UUID]
    subject: str
    sender: str
    recipients: List[str]
    body: str
    received_at: datetime
    processing_status: str
    raw_extraction: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True
