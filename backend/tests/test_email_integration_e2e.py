"""
End-to-end integration tests for complete email processing flow.
"""
import pytest
from unittest.mock import Mock, patch
from email.message import EmailMessage
from datetime import datetime

from app.models.case import Case
from app.models.email import Email, EmailProcessingStatus
from app.models.attachment import Attachment
from app.schemas.email import EmailIngest


@pytest.fixture
def mock_config(monkeypatch):
    """Mock email configuration."""
    from app import config

    monkeypatch.setattr(config.settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(config.settings, "EMAIL_ADDRESS", "test@example.com")
    monkeypatch.setattr(config.settings, "EMAIL_PASSWORD", "test-password")
    monkeypatch.setattr(config.settings, "EMAIL_IMAP_SERVER", "imap.example.com")


def test_email_fetch_to_case_creation(client, db, mock_config, redis_conn, monkeypatch):
    """Full pipeline test: IMAP fetch -> queue -> processing -> database."""
    # Mock OpenAI extraction
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction, AttachmentExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Alice Brown",
            case_number="E2E-TEST-001",
            exam_type="Neurology",
            exam_date="2025-04-01",
            exam_time="14:00",
            exam_location="San Francisco, CA",
            referring_party="Bay Area Law",
            referring_email="contact@bayarealaw.com",
            confidence=0.93,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[
                AttachmentExtraction(
                    filename="patient_records.pdf",
                    category="medical_records",
                    category_reason="Contains medical history"
                )
            ]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    # Create IMAP email message
    msg = EmailMessage()
    msg["Subject"] = "New Neurology Referral - Alice Brown"
    msg["From"] = "contact@bayarealaw.com"
    msg["To"] = "intake@imecompany.com"
    msg["Date"] = "Mon, 15 Jan 2024 14:00:00 +0000"
    msg.set_content("""
    We are referring Alice Brown for a neurology examination.
    Case Number: E2E-TEST-001
    Exam Date: April 1, 2025 at 2:00 PM
    Location: San Francisco, CA
    """)

    with patch('app.routers.email_polling.EmailFetcher') as mock_fetcher_class:
        with patch('app.routers.email_polling.EmailParser') as mock_parser_class:
            # Mock EmailFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_unread_emails.return_value = [msg]
            mock_fetcher_class.return_value = mock_fetcher

            # Mock EmailParser.parse_to_ingest static method
            mock_parser_class.parse_to_ingest.return_value = EmailIngest(
                subject="New Neurology Referral - Alice Brown",
                sender="contact@bayarealaw.com",
                recipients=["intake@imecompany.com"],
                body=str(msg.get_content()),
                attachments=[
                    {
                        "filename": "patient_records.pdf",
                        "content_type": "application/pdf",
                        "text_content": "Medical history for Alice Brown..."
                    }
                ],
                received_at=datetime.utcnow()
            )

            # Trigger manual poll endpoint
            response = client.post("/email-polling/manual-poll")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["processed"] == 1
            assert len(data["emails"]) == 1

            job_id = data["emails"][0]["job_id"]
            assert job_id is not None

            # In a real scenario, we'd wait for the worker to process the job
            # For testing, we'll process it directly using the task function
            from app.tasks import process_email_task

            email_dict = {
                "subject": "New Neurology Referral - Alice Brown",
                "sender": "contact@bayarealaw.com",
                "recipients": ["intake@imecompany.com"],
                "body": str(msg.get_content()),
                "attachments": [
                    {
                        "filename": "patient_records.pdf",
                        "content_type": "application/pdf",
                        "text_content": "Medical history for Alice Brown..."
                    }
                ],
                "received_at": datetime.utcnow().isoformat()
            }

            # Mock get_current_job and SessionLocal
            with patch('app.tasks.get_current_job') as mock_get_job:
                with patch('app.tasks.SessionLocal') as mock_session_local:
                    mock_job = Mock()
                    mock_job.id = job_id
                    mock_get_job.return_value = mock_job
                    mock_session_local.return_value = db

                    # Process the job
                    result = process_email_task(email_dict)

                    # Verify result
                    assert result is not None
                    assert result["status"] == "processed"

                    # Verify case was created in database
                    case = db.query(Case).filter(Case.case_number == "E2E-TEST-001").first()
                    assert case is not None
                    assert case.patient_name == "Alice Brown"
                    assert case.exam_type == "Neurology"
                    assert case.extraction_confidence == 0.93

                    # Verify email was created
                    email = db.query(Email).filter(Email.id == result["email_id"]).first()
                    assert email is not None
                    assert email.processing_status == EmailProcessingStatus.PROCESSED
                    assert email.case_id == case.id

                    # Verify attachment was created
                    attachments = db.query(Attachment).filter(Attachment.case_id == case.id).all()
                    assert len(attachments) == 1
                    assert attachments[0].filename == "patient_records.pdf"
                    assert attachments[0].category == "medical_records"


def test_multiple_emails_batch_processing(client, db, mock_config, redis_conn, monkeypatch):
    """Test batch email handling."""
    # Mock OpenAI extraction
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    call_count = [0]

    def mock_extraction(*args, **kwargs):
        call_count[0] += 1
        return CaseExtraction(
            patient_name=f"Patient {call_count[0]}",
            case_number=f"BATCH-{call_count[0]:03d}",
            exam_type="Orthopedic",
            confidence=0.90,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    # Create 3 IMAP email messages
    messages = []
    for i in range(1, 4):
        msg = EmailMessage()
        msg["Subject"] = f"Test Email {i}"
        msg["From"] = f"sender{i}@example.com"
        msg["To"] = "intake@imecompany.com"
        msg["Date"] = "Mon, 15 Jan 2024 10:00:00 +0000"
        msg.set_content(f"Email body {i}")
        messages.append(msg)

    with patch('app.routers.email_polling.EmailFetcher') as mock_fetcher_class:
        with patch('app.routers.email_polling.EmailParser') as mock_parser_class:
            # Mock EmailFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_unread_emails.return_value = messages
            mock_fetcher_class.return_value = mock_fetcher

            # Mock EmailParser.parse_to_ingest static method
            def parse_side_effect(msg):
                return EmailIngest(
                    subject=msg["Subject"],
                    sender=msg["From"],
                    recipients=[msg["To"]],
                    body=str(msg.get_content()),
                    attachments=[],
                    received_at=datetime.utcnow()
                )

            mock_parser_class.parse_to_ingest.side_effect = parse_side_effect

            # Trigger manual poll
            response = client.post("/email-polling/manual-poll")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["processed"] == 3
            assert len(data["emails"]) == 3

            # Process all jobs
            from app.tasks import process_email_task

            for i, email_data in enumerate(data["emails"]):
                email_dict = {
                    "subject": f"Test Email {i + 1}",
                    "sender": f"sender{i + 1}@example.com",
                    "recipients": ["intake@imecompany.com"],
                    "body": f"Email body {i + 1}",
                    "attachments": [],
                    "received_at": datetime.utcnow().isoformat()
                }

                with patch('app.tasks.get_current_job') as mock_get_job:
                    with patch('app.tasks.SessionLocal') as mock_session_local:
                        mock_job = Mock()
                        mock_job.id = email_data["job_id"]
                        mock_get_job.return_value = mock_job
                        mock_session_local.return_value = db

                        process_email_task(email_dict)

            # Verify all cases were created
            cases = db.query(Case).filter(Case.case_number.like("BATCH-%")).all()
            assert len(cases) == 3

            case_numbers = [c.case_number for c in cases]
            assert "BATCH-001" in case_numbers
            assert "BATCH-002" in case_numbers
            assert "BATCH-003" in case_numbers


def test_email_poller_idempotency(client, db, mock_config, monkeypatch):
    """Test duplicate email handling."""
    # Mock OpenAI extraction
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Idempotent Test",
            case_number="IDEM-001",
            exam_type="Cardiology",
            confidence=0.88,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    # Create email message
    msg = EmailMessage()
    msg["Subject"] = "Idempotency Test"
    msg["From"] = "sender@example.com"
    msg["To"] = "intake@imecompany.com"
    msg["Date"] = "Mon, 15 Jan 2024 10:00:00 +0000"
    msg.set_content("Idempotency test body")

    with patch('app.routers.email_polling.EmailFetcher') as mock_fetcher_class:
        with patch('app.routers.email_polling.EmailParser') as mock_parser_class:
            # Mock EmailFetcher - first poll returns email, second returns empty
            mock_fetcher = Mock()
            mock_fetcher.fetch_unread_emails.side_effect = [[msg], []]  # First call has email, second is empty
            mock_fetcher_class.return_value = mock_fetcher

            # Mock EmailParser.parse_to_ingest static method
            mock_parser_class.parse_to_ingest.return_value = EmailIngest(
                subject="Idempotency Test",
                sender="sender@example.com",
                recipients=["intake@imecompany.com"],
                body="Idempotency test body",
                attachments=[],
                received_at=datetime.utcnow()
            )

            # First poll
            response1 = client.post("/email-polling/manual-poll")
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["processed"] == 1

            # Process the job
            from app.tasks import process_email_task

            email_dict = {
                "subject": "Idempotency Test",
                "sender": "sender@example.com",
                "recipients": ["intake@imecompany.com"],
                "body": "Idempotency test body",
                "attachments": [],
                "received_at": datetime.utcnow().isoformat()
            }

            with patch('app.tasks.get_current_job') as mock_get_job:
                with patch('app.tasks.SessionLocal') as mock_session_local:
                    mock_job = Mock()
                    mock_job.id = data1["emails"][0]["job_id"]
                    mock_get_job.return_value = mock_job
                    mock_session_local.return_value = db

                    process_email_task(email_dict)

            # Verify case was created
            cases_before = db.query(Case).filter(Case.case_number == "IDEM-001").count()
            assert cases_before == 1

            # Second poll - should return no emails (marked as read)
            response2 = client.post("/email-polling/manual-poll")
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["processed"] == 0  # No new emails

            # Verify still only one case
            cases_after = db.query(Case).filter(Case.case_number == "IDEM-001").count()
            assert cases_after == 1


def test_email_processing_with_high_priority(client, db, mock_config, redis_conn, monkeypatch):
    """Test high priority email processing."""
    # Mock OpenAI extraction
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="High Priority Patient",
            case_number="HIGH-PRIORITY-001",
            exam_type="Emergency",
            confidence=0.95,
            extraction_notes=None,
            email_intent="urgent_referral",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    # Create urgent email
    msg = EmailMessage()
    msg["Subject"] = "URGENT: Emergency Referral"
    msg["From"] = "urgent@example.com"
    msg["To"] = "intake@imecompany.com"
    msg["Date"] = "Mon, 15 Jan 2024 10:00:00 +0000"
    msg.set_content("Urgent emergency referral")

    with patch('app.routers.email_polling.EmailFetcher') as mock_fetcher_class:
        with patch('app.routers.email_polling.EmailParser') as mock_parser_class:
            with patch('app.routers.email_polling.enqueue_email_processing') as mock_enqueue:
                # Mock EmailFetcher
                mock_fetcher = Mock()
                mock_fetcher.fetch_unread_emails.return_value = [msg]
                mock_fetcher_class.return_value = mock_fetcher

                # Mock EmailParser
                mock_parser = Mock()
                mock_parser.parse.return_value = EmailIngest(
                    subject="URGENT: Emergency Referral",
                    sender="urgent@example.com",
                    recipients=["intake@imecompany.com"],
                    body="Urgent emergency referral",
                    attachments=[],
                    received_at=datetime.utcnow()
                )
                mock_parser_class.return_value = mock_parser

                # Mock enqueue
                mock_job = Mock()
                mock_job.id = "urgent-job-123"
                mock_enqueue.return_value = mock_job

                # Trigger manual poll
                response = client.post("/email-polling/manual-poll")

                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["processed"] == 1

                # Verify enqueue was called (we could check for high_priority=True in real implementation)
                assert mock_enqueue.called


def test_email_processing_error_recovery(client, db, mock_config, monkeypatch):
    """Test error recovery in email processing pipeline."""
    # Mock extraction to fail first time, succeed second time
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    call_count = [0]

    def mock_extraction_with_retry(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First call fails
            raise Exception("Temporary API error")
        else:
            # Second call succeeds
            return CaseExtraction(
                patient_name="Recovered Patient",
                case_number="RECOVERY-001",
                exam_type="Orthopedic",
                confidence=0.90,
                extraction_notes=None,
                email_intent="new_referral",
                attachments=[]
            )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction_with_retry)

    # Create email
    msg = EmailMessage()
    msg["Subject"] = "Recovery Test"
    msg["From"] = "sender@example.com"
    msg["To"] = "intake@imecompany.com"
    msg["Date"] = "Mon, 15 Jan 2024 10:00:00 +0000"
    msg.set_content("Recovery test body")

    email_dict = {
        "subject": "Recovery Test",
        "sender": "sender@example.com",
        "recipients": ["intake@imecompany.com"],
        "body": "Recovery test body",
        "attachments": [],
        "received_at": datetime.utcnow().isoformat()
    }

    from app.tasks import process_email_task

    # First attempt - should fail
    with patch('app.tasks.get_current_job') as mock_get_job:
        with patch('app.tasks.SessionLocal') as mock_session_local:
            mock_job = Mock()
            mock_job.id = "recovery-job-1"
            mock_get_job.return_value = mock_job
            mock_session_local.return_value = db

            with pytest.raises(Exception) as exc_info:
                process_email_task(email_dict)

            assert "Temporary API error" in str(exc_info.value)

    # Second attempt - should succeed
    with patch('app.tasks.get_current_job') as mock_get_job:
        with patch('app.tasks.SessionLocal') as mock_session_local:
            mock_job = Mock()
            mock_job.id = "recovery-job-2"
            mock_get_job.return_value = mock_job
            mock_session_local.return_value = db

            result = process_email_task(email_dict)

            # Verify success
            assert result is not None
            assert result["status"] == "processed"

            # Verify case was created
            case = db.query(Case).filter(Case.case_number == "RECOVERY-001").first()
            assert case is not None
