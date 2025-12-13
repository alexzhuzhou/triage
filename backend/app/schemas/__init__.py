"""
Pydantic schemas for API request/response validation.
"""
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse
from app.schemas.email import EmailIngest, EmailResponse
from app.schemas.extraction import CaseExtraction, AttachmentExtraction, EmailIntent

__all__ = [
    "CaseCreate",
    "CaseUpdate",
    "CaseResponse",
    "EmailIngest",
    "EmailResponse",
    "CaseExtraction",
    "AttachmentExtraction",
    "EmailIntent",
]
