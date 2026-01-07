"""
Tests for worker task processing.
"""
import pytest
from unittest.mock import patch, Mock
from datetime import datetime

from app.tasks import process_email_task
from app.schemas.email import EmailIngest
from app.models.case import Case
from app.models.email import Email, EmailProcessingStatus


def test_process_email_task_success(db, monkeypatch):
    """Test successful email processing."""
    # Mock OpenAI extraction at the ingestion module level
    from app.schemas.extraction import CaseExtraction, AttachmentExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="John Doe",
            case_number="WORKER-TEST-001",
            exam_type="Orthopedic",
            exam_date="2025-03-15",
            exam_time="10:00",
            exam_location="Los Angeles, CA",
            referring_party="Test Law Firm",
            referring_email="test@testlaw.com",
            confidence=0.95,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr("app.services.ingestion.extract_case_from_email", mock_extraction)

    # Create email data dict
    email_data_dict = {
        "subject": "Worker Test Email",
        "sender": "test@example.com",
        "recipients": ["intake@test.com"],
        "body": "Test body for worker",
        "attachments": [],
        "received_at": datetime.utcnow().isoformat()
    }

    # Mock get_current_job to avoid RQ context requirement
    # Also mock SessionLocal to use test database
    with patch('app.tasks.get_current_job') as mock_get_job:
        with patch('app.tasks.SessionLocal') as mock_session_local:
            mock_job = Mock()
            mock_job.id = "test-worker-job-123"
            mock_get_job.return_value = mock_job

            # Use test database session
            mock_session_local.return_value = db

            # Process the email task
            result = process_email_task(email_data_dict)

        # Verify result format
        assert result is not None
        assert "job_id" in result
        assert result["job_id"] == "test-worker-job-123"
        assert "email_id" in result
        assert "case_id" in result
        assert "status" in result
        assert result["status"] == "processed"
        assert "subject" in result

        # Verify database records
        case = db.query(Case).filter(Case.case_number == "WORKER-TEST-001").first()
        assert case is not None
        assert case.patient_name == "John Doe"
        assert case.exam_type == "Orthopedic"

        email = db.query(Email).filter(Email.id == result["email_id"]).first()
        assert email is not None
        assert email.processing_status == EmailProcessingStatus.PROCESSED
        assert email.case_id is not None


def test_process_email_task_extraction_failure(db, monkeypatch):
    """Test graceful failure handling."""
    # Mock OpenAI extraction to return fallback
    from app.schemas.extraction import CaseExtraction

    def mock_extraction_failure(*args, **kwargs):
        # Simulate extraction service's fallback behavior
        return CaseExtraction(
            patient_name="EXTRACTION_FAILED",
            case_number="UNKNOWN_test@example.com",
            exam_type="Unknown",
            attachments=[],
            confidence=0.0,
            extraction_notes="Extraction failed: API Error",
            email_intent="other"
        )

    monkeypatch.setattr("app.services.ingestion.extract_case_from_email", mock_extraction_failure)

    # Create email data dict
    email_data_dict = {
        "subject": "Worker Failure Test",
        "sender": "test@example.com",
        "recipients": ["intake@test.com"],
        "body": "Test body",
        "attachments": [],
        "received_at": datetime.utcnow().isoformat()
    }

    # Mock get_current_job and SessionLocal
    with patch('app.tasks.get_current_job') as mock_get_job:
        with patch('app.tasks.SessionLocal') as mock_session_local:
            mock_job = Mock()
            mock_job.id = "test-failure-job-456"
            mock_get_job.return_value = mock_job
            mock_session_local.return_value = db

            # Process the email task - should not crash
            result = process_email_task(email_data_dict)

        # Verify result
        assert result is not None
        assert result["status"] == "processed"

        # Verify case was created with failure indicators
        case = db.query(Case).filter(Case.case_number == "UNKNOWN_test@example.com").first()
        assert case is not None
        assert case.extraction_confidence == 0.0
        assert case.patient_name == "EXTRACTION_FAILED"


def test_process_email_task_database_error(monkeypatch):
    """Test that database errors are raised for retry."""
    # Mock extraction to succeed
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Test Patient",
            case_number="TEST-DB-ERROR",
            exam_type="Orthopedic",
            confidence=0.90,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr("app.services.ingestion.extract_case_from_email", mock_extraction)

    # Mock SessionLocal to raise database error
    with patch('app.tasks.SessionLocal') as mock_session_local:
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database connection failed")
        mock_session_local.return_value = mock_db

        # Create email data dict
        email_data_dict = {
            "subject": "DB Error Test",
            "sender": "test@example.com",
            "recipients": ["intake@test.com"],
            "body": "Test body",
            "attachments": [],
            "received_at": datetime.utcnow().isoformat()
        }

        # Mock get_current_job
        with patch('app.tasks.get_current_job') as mock_get_job:
            mock_job = Mock()
            mock_job.id = "test-db-error-job"
            mock_get_job.return_value = mock_job

            # Process should raise exception for RQ retry
            with pytest.raises(Exception) as exc_info:
                process_email_task(email_data_dict)

            assert "Database connection failed" in str(exc_info.value)


def test_process_email_task_retry_logging(db, monkeypatch, caplog):
    """Test that retry information is logged."""
    import logging
    caplog.set_level(logging.INFO)

    # Mock extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Test Patient",
            case_number="TEST-RETRY-LOG",
            exam_type="Orthopedic",
            confidence=0.90,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr("app.services.ingestion.extract_case_from_email", mock_extraction)

    # Create email data dict
    email_data_dict = {
        "subject": "Retry Log Test",
        "sender": "test@example.com",
        "recipients": ["intake@test.com"],
        "body": "Test body",
        "attachments": [],
        "received_at": datetime.utcnow().isoformat()
    }

    # Mock get_current_job and SessionLocal
    with patch('app.tasks.get_current_job') as mock_get_job:
        with patch('app.tasks.SessionLocal') as mock_session_local:
            mock_job = Mock()
            mock_job.id = "test-retry-log-job"
            mock_get_job.return_value = mock_job
            mock_session_local.return_value = db

            # Process the task
            result = process_email_task(email_data_dict)

        # Verify logging
        assert result is not None

        # Check that job ID is logged
        log_messages = [record.message for record in caplog.records]
        job_logged = any("test-retry-log-job" in msg for msg in log_messages)
        assert job_logged

        # Check that subject is logged
        subject_logged = any("Retry Log Test" in msg for msg in log_messages)
        assert subject_logged


def test_process_email_task_invalid_email_data():
    """Test that invalid email data raises exception."""
    # Create invalid email data (missing required fields)
    invalid_data = {
        "subject": "Invalid Test"
        # Missing sender, recipients, body, etc.
    }

    # Mock get_current_job
    with patch('app.tasks.get_current_job') as mock_get_job:
        mock_job = Mock()
        mock_job.id = "test-invalid-job"
        mock_get_job.return_value = mock_job

        # Process should raise validation error
        with pytest.raises(Exception):
            process_email_task(invalid_data)


def test_process_email_task_matching_existing_case(db, monkeypatch):
    """Test that task correctly matches existing cases."""
    from app.models.case import Case as CaseModel

    # Create an existing case
    existing_case = CaseModel(
        case_number="WORKER-MATCH-001",
        patient_name="Jane Smith",
        exam_type="Psychiatric",
        extraction_confidence=0.85
    )
    db.add(existing_case)
    db.commit()
    existing_case_id = existing_case.id

    # Mock extraction to return same case number
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Jane Smith",
            case_number="WORKER-MATCH-001",
            exam_type="Psychiatric",
            confidence=0.92,  # Higher confidence
            extraction_notes=None,
            email_intent="scheduling_update",
            attachments=[]
        )

    monkeypatch.setattr("app.services.ingestion.extract_case_from_email", mock_extraction)

    # Create email data dict
    email_data_dict = {
        "subject": "Worker Match Test",
        "sender": "test@example.com",
        "recipients": ["intake@test.com"],
        "body": "Follow-up for existing case",
        "attachments": [],
        "received_at": datetime.utcnow().isoformat()
    }

    # Mock get_current_job and SessionLocal
    with patch('app.tasks.get_current_job') as mock_get_job:
        with patch('app.tasks.SessionLocal') as mock_session_local:
            mock_job = Mock()
            mock_job.id = "test-match-job"
            mock_get_job.return_value = mock_job
            mock_session_local.return_value = db

            # Process the task
            result = process_email_task(email_data_dict)

        # Verify result matches existing case
        assert result is not None
        assert result["case_id"] == str(existing_case_id)

        # Verify case was updated (higher confidence) - re-query instead of refresh
        updated_case = db.query(CaseModel).filter(CaseModel.id == existing_case_id).first()
        assert updated_case is not None
        assert updated_case.extraction_confidence == 0.92


def test_process_email_task_with_attachments(db, monkeypatch):
    """Test processing email with attachments."""
    # Mock extraction
    from app.schemas.extraction import CaseExtraction, AttachmentExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Bob Johnson",
            case_number="WORKER-ATTACH-001",
            exam_type="Cardiology",
            confidence=0.88,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[
                AttachmentExtraction(
                    filename="medical_records.pdf",
                    category="medical_records",
                    category_reason="Contains patient medical history"
                ),
                AttachmentExtraction(
                    filename="referral_letter.pdf",
                    category="cover_letter",
                    category_reason="Official referral document"
                )
            ]
        )

    monkeypatch.setattr("app.services.ingestion.extract_case_from_email", mock_extraction)

    # Create email data dict with attachments
    email_data_dict = {
        "subject": "Worker Attachment Test",
        "sender": "test@example.com",
        "recipients": ["intake@test.com"],
        "body": "Email with attachments",
        "attachments": [
            {
                "filename": "medical_records.pdf",
                "content_type": "application/pdf",
                "text_content": "Medical history..."
            },
            {
                "filename": "referral_letter.pdf",
                "content_type": "application/pdf",
                "text_content": "Referral letter..."
            }
        ],
        "received_at": datetime.utcnow().isoformat()
    }

    # Mock get_current_job and SessionLocal
    with patch('app.tasks.get_current_job') as mock_get_job:
        with patch('app.tasks.SessionLocal') as mock_session_local:
            mock_job = Mock()
            mock_job.id = "test-attach-job"
            mock_get_job.return_value = mock_job
            mock_session_local.return_value = db

            # Process the task
            result = process_email_task(email_data_dict)

        # Verify result
        assert result is not None

        # Verify case and attachments were created
        from app.models.attachment import Attachment
        case = db.query(Case).filter(Case.case_number == "WORKER-ATTACH-001").first()
        assert case is not None

        attachments = db.query(Attachment).filter(Attachment.case_id == case.id).all()
        assert len(attachments) == 2

        filenames = [a.filename for a in attachments]
        assert "medical_records.pdf" in filenames
        assert "referral_letter.pdf" in filenames
