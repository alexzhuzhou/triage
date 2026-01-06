"""
Tests for email ingestion service.
"""
import pytest
from datetime import datetime

from app.schemas.email import EmailIngest
from app.services.ingestion import process_email, find_or_create_case
from app.models.case import Case
from app.models.email import EmailProcessingStatus


@pytest.fixture
def sample_email_data():
    """Sample email data for testing."""
    return EmailIngest(
        subject="New IME Referral – John Doe – Case #TEST-001",
        sender="referrals@testlaw.com",
        recipients=["intake@imecompany.com"],
        body="""Good morning,

We are referring a new Independent Medical Examination for:

Patient: John Doe
Case Number: TEST-001
Exam Type: Orthopedic
Exam Date: March 15, 2025
Exam Time: 10:00 AM
Location: Los Angeles, CA

Please confirm receipt.

Thank you,
Test Law Firm
""",
        attachments=[
            {
                "filename": "medical_records.pdf",
                "content_type": "application/pdf",
                "text_content": "Medical records for John Doe including treatment history..."
            }
        ],
        received_at=datetime.utcnow()
    )


def test_process_email_creates_case(db, sample_email_data, monkeypatch):
    """Test that processing an email creates a case."""
    # Mock the OpenAI extraction to avoid API calls in tests
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction, AttachmentExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="John Doe",
            case_number="TEST-001",
            exam_type="Orthopedic",
            exam_date="2025-03-15",
            exam_time="10:00",
            exam_location="Los Angeles, CA",
            referring_party="Test Law Firm",
            referring_email="referrals@testlaw.com",
            confidence=0.95,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[
                AttachmentExtraction(
                    filename="medical_records.pdf",
                    category="medical_records",
                    category_reason=None
                )
            ]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    # Process the email
    email = process_email(db, sample_email_data)

    # Assertions
    assert email.processing_status == EmailProcessingStatus.PROCESSED
    assert email.case_id is not None
    assert email.raw_extraction is not None

    # Verify case was created
    case = db.query(Case).filter(Case.case_number == "TEST-001").first()
    assert case is not None
    assert case.patient_name == "John Doe"
    assert case.exam_type == "Orthopedic"
    assert case.extraction_confidence == 0.95


def test_process_email_matches_existing_case(db, sample_email_data, monkeypatch):
    """Test that processing a follow-up email matches existing case."""
    # Mock the OpenAI extraction
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction, AttachmentExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="John Doe",
            case_number="TEST-001",
            exam_type="Orthopedic",
            confidence=0.90,
            extraction_notes=None,
            email_intent="scheduling_update",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    # Create initial case
    initial_case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic",
        extraction_confidence=0.85
    )
    db.add(initial_case)
    db.commit()
    initial_case_id = initial_case.id

    # Process the email
    email = process_email(db, sample_email_data)

    # Verify it matched the existing case
    assert email.case_id == initial_case_id

    # Refresh the case from database to get updated values
    db.refresh(initial_case)

    # Verify case was updated (higher confidence)
    assert initial_case.extraction_confidence == 0.90


def test_process_email_handles_extraction_failure(db, sample_email_data, monkeypatch):
    """Test that email processing handles extraction failures gracefully."""
    # Mock the extraction service to return a fallback response
    # (The extraction service catches exceptions and returns fallback CaseExtraction)
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction_failure(*args, **kwargs):
        # Simulate what extraction.py does when OpenAI fails
        return CaseExtraction(
            patient_name="EXTRACTION_FAILED",
            case_number="UNKNOWN_test@example.com",
            exam_type="Unknown",
            attachments=[],
            confidence=0.0,
            extraction_notes="Extraction failed: API Error",
            email_intent="other"
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction_failure)

    # Process the email - should not crash
    email = process_email(db, sample_email_data)

    # Verify email was saved despite failure
    assert email is not None
    assert email.processing_status == EmailProcessingStatus.PROCESSED

    # Verify case was created with failure indicators
    case = db.query(Case).filter(Case.id == email.case_id).first()
    assert case.extraction_confidence == 0.0
    assert case.patient_name == "EXTRACTION_FAILED"
