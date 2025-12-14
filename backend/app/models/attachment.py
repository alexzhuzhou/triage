"""
Attachment model - represents email attachments.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class AttachmentCategory(str, enum.Enum):
    """Attachment category enumeration."""
    MEDICAL_RECORDS = "medical_records"
    DECLARATION = "declaration"
    COVER_LETTER = "cover_letter"
    OTHER = "other"


class Attachment(Base):
    """
    Attachment model representing an email attachment.

    Links to both the source email and the associated case.
    Includes categorization and content preview for context.
    """
    __tablename__ = "attachments"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)

    # File information
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)  # MIME type
    content_preview = Column(Text, nullable=True)  # First 500 chars

    # File storage (for future S3 integration)
    file_path = Column(String, nullable=True)  # S3 path: "s3://bucket/cases/{case_number}/file.pdf"
    file_size = Column(Integer, nullable=True)  # Size in bytes
    storage_provider = Column(String, nullable=True)  # "s3", "azure", "local", etc.

    # Categorization (from LLM extraction)
    category = Column(Enum(AttachmentCategory), nullable=False)
    category_reason = Column(Text, nullable=True)  # Explanation for "other" category

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    email = relationship("Email", back_populates="attachments")
    case = relationship("Case", back_populates="attachments")

    # Indexes for faster lookups
    __table_args__ = (
        Index('ix_attachments_email_id', 'email_id'),
        Index('ix_attachments_case_id', 'case_id'),
        Index('ix_attachments_category', 'category'),
    )

    def __repr__(self):
        return f"<Attachment {self.filename} - {self.category}>"
