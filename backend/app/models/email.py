"""
Email model - represents source emails that are processed.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class EmailProcessingStatus(str, enum.Enum):
    """Email processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Email(Base):
    """
    Email model representing an inbound email.

    Stores the raw email data and links to the extracted case.
    Multiple emails can reference the same case (follow-ups, updates, etc.).
    """
    __tablename__ = "emails"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to case
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)

    # Email metadata
    subject = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    recipients = Column(JSON, nullable=False)  # List of email addresses
    body = Column(Text, nullable=False)
    received_at = Column(DateTime, nullable=False)

    # Processing metadata
    processing_status = Column(
        Enum(EmailProcessingStatus),
        default=EmailProcessingStatus.PENDING,
        nullable=False
    )
    raw_extraction = Column(JSON, nullable=True)  # Full LLM response for debugging
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="emails")
    attachments = relationship("Attachment", back_populates="email", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Email {self.id} - {self.subject}>"
