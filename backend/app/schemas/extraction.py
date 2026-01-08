"""
Pydantic schemas for LLM extraction.

These schemas define the structure that the LLM should extract from emails.
"""
from typing import List, Optional, Literal
from datetime import date, time
from pydantic import BaseModel, Field, ConfigDict


class EmailIntent(str):
    """Email intent categories."""
    NEW_REFERRAL = "new_referral"
    SCHEDULING_UPDATE = "scheduling_update"
    DOCUMENT_SUBMISSION = "document_submission"
    INQUIRY = "inquiry"
    OTHER = "other"


class AttachmentExtraction(BaseModel):
    """Schema for extracted attachment information."""

    model_config = ConfigDict(extra='forbid')

    filename: str = Field(description="Name of the attachment file")
    category: Literal["medical_records", "declaration", "cover_letter", "other"] = Field(
        description="Category of the attachment"
    )
    category_reason: Optional[str] = Field(
        description="Explanation for categorization, especially for 'other' category"
    )


class CaseExtraction(BaseModel):
    """
    Schema for case data extracted from an email using LLM.

    This structure is used both for prompting the LLM and parsing its response.
    """

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "patient_name": "John Doe",
                "case_number": "NF-39281",
                "exam_type": "Orthopedic",
                "exam_date": "2025-03-15",
                "exam_time": "10:00",
                "exam_location": "Los Angeles, CA",
                "referring_party": "Smith & Associates Law Firm",
                "referring_email": "referrals@smithlaw.com",
                "report_due_date": "2025-03-30",
                "confidence": 0.95,
                "extraction_notes": None,
                "email_intent": "new_referral",
                "attachments": [
                    {
                        "filename": "medical_records.pdf",
                        "category": "medical_records",
                        "category_reason": None
                    }
                ]
            }
        }
    )

    # Required fields
    patient_name: str = Field(description="Full name of the patient/claimant")
    case_number: str = Field(
        description="Case or file number (preserve original formatting, e.g., 'NF-39281')"
    )
    exam_type: str = Field(
        description="Type of IME examination (e.g., Orthopedic, Neurology, Psychiatric)"
    )
    attachments: List[AttachmentExtraction] = Field(
        description="List of attachments with categorization (provide empty array if none)"
    )

    # Optional fields (can be null)
    exam_date: Optional[str] = Field(
        description="Date of examination in ISO format (YYYY-MM-DD) if mentioned"
    )
    exam_time: Optional[str] = Field(
        description="Time of examination in HH:MM format if mentioned"
    )
    exam_location: Optional[str] = Field(
        description="Location of examination (city, state, or full address)"
    )
    referring_party: Optional[str] = Field(
        description="Name of referring law firm or organization"
    )
    referring_email: Optional[str] = Field(
        description="Contact email of referring party"
    )
    report_due_date: Optional[str] = Field(
        description="Deadline for report submission in ISO format (YYYY-MM-DD)"
    )

    # Metadata
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0 for the extraction quality",
        ge=0.0,
        le=1.0
    )
    extraction_notes: Optional[str] = Field(
        description="Notes about ambiguities, uncertainties, or assumptions made during extraction"
    )
    email_intent: str = Field(
        description="Intent classification of the email (new_referral, scheduling_update, etc.)"
    )
