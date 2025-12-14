"""
Case model - represents an IME case.
"""
import uuid
from datetime import datetime, date, time
from sqlalchemy import Column, String, Date, Time, DateTime, Float, Text, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class CaseStatus(str, enum.Enum):
    """Case status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"


class Case(Base):
    """
    Case model representing an IME case.

    A case is the primary entity that emails and attachments link to.
    Multiple emails can reference the same case.
    """
    __tablename__ = "cases"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Case identification
    case_number = Column(String, unique=True, index=True, nullable=False)
    patient_name = Column(String, nullable=False)

    # Exam details
    exam_type = Column(String, nullable=False)  # e.g., Orthopedic, Neurology
    exam_date = Column(Date, nullable=True)
    exam_time = Column(Time, nullable=True)
    exam_location = Column(String, nullable=True)

    # Referring party information
    referring_party = Column(String, nullable=True)  # Law firm or organization
    referring_email = Column(String, nullable=True)

    # Deadlines and status
    report_due_date = Column(Date, nullable=True)
    status = Column(Enum(CaseStatus), default=CaseStatus.PENDING, nullable=False)

    # Extraction metadata
    extraction_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    emails = relationship("Email", back_populates="case", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="case", cascade="all, delete-orphan")

    # Indexes for faster lookups
    __table_args__ = (
        Index('ix_cases_status', 'status'),
        Index('ix_cases_extraction_confidence', 'extraction_confidence'),
        Index('ix_cases_created_at', 'created_at'),
        Index('ix_cases_exam_date', 'exam_date'),
    )

    def __repr__(self):
        return f"<Case {self.case_number} - {self.patient_name}>"
