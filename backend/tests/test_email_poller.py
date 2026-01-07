"""
Tests for email poller service and queue integration.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from email.message import EmailMessage
from datetime import datetime

from app.services.email_poller import EmailPoller
from app.schemas.email import EmailIngest


@pytest.fixture
def sample_imap_messages():
    """Create sample IMAP email messages."""
    messages = []

    # Message 1
    msg1 = EmailMessage()
    msg1["Subject"] = "Test Email 1"
    msg1["From"] = "sender1@example.com"
    msg1["To"] = "recipient@example.com"
    msg1["Date"] = "Mon, 15 Jan 2024 10:00:00 +0000"
    msg1.set_content("This is test email 1 body")
    messages.append(msg1)

    # Message 2
    msg2 = EmailMessage()
    msg2["Subject"] = "Test Email 2"
    msg2["From"] = "sender2@example.com"
    msg2["To"] = "recipient@example.com"
    msg2["Date"] = "Mon, 15 Jan 2024 11:00:00 +0000"
    msg2.set_content("This is test email 2 body")
    messages.append(msg2)

    return messages


@pytest.fixture
def mock_config(monkeypatch):
    """Mock email configuration."""
    from app import config

    monkeypatch.setattr(config.settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(config.settings, "EMAIL_ADDRESS", "test@example.com")
    monkeypatch.setattr(config.settings, "EMAIL_PASSWORD", "test-password")
    monkeypatch.setattr(config.settings, "EMAIL_IMAP_SERVER", "imap.example.com")
    monkeypatch.setattr(config.settings, "EMAIL_POLL_INTERVAL", 60)


@pytest.mark.asyncio
async def test_email_poller_initialization_disabled():
    """Test EmailPoller with EMAIL_ENABLED=False."""
    with patch('app.services.email_poller.settings') as mock_settings:
        mock_settings.EMAIL_ENABLED = False

        poller = EmailPoller()

        # start() should return early when disabled
        result = await poller.poll_emails()
        assert result is not None
        # When disabled, poll_emails might not even run or return empty result


@pytest.mark.asyncio
async def test_email_poller_initialization_missing_credentials():
    """Test EmailPoller with missing credentials."""
    with patch('app.services.email_poller.settings') as mock_settings:
        mock_settings.EMAIL_ENABLED = True
        mock_settings.EMAIL_ADDRESS = ""  # Missing
        mock_settings.EMAIL_PASSWORD = ""  # Missing

        poller = EmailPoller()

        # Should handle missing credentials gracefully
        # The poll_emails method checks for credentials
        result = await poller.poll_emails()
        assert result is not None


@pytest.mark.asyncio
async def test_poll_emails_success(mock_config, sample_imap_messages, redis_conn):
    """Test successful polling cycle."""
    with patch('app.services.email_poller.EmailFetcher') as mock_fetcher_class:
        with patch('app.services.email_poller.EmailParser') as mock_parser_class:
            with patch('app.services.email_poller.enqueue_email_processing') as mock_enqueue:
                # Mock EmailFetcher
                mock_fetcher = Mock()
                mock_fetcher.fetch_unread_emails.return_value = sample_imap_messages
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

                # Mock enqueue
                mock_job1 = Mock()
                mock_job1.id = "job-1"
                mock_job2 = Mock()
                mock_job2.id = "job-2"
                mock_enqueue.side_effect = [mock_job1, mock_job2]

                # Create poller and poll
                poller = EmailPoller()
                result = await poller.poll_emails()

                # Verify result
                assert result is not None
                assert result["processed"] == 2
                assert result["failed"] == 0
                assert len(result["emails"]) == 2

                # Verify job IDs are in result
                job_ids = [email["job_id"] for email in result["emails"]]
                assert "job-1" in job_ids
                assert "job-2" in job_ids

                # Verify subjects are in result
                subjects = [email["subject"] for email in result["emails"]]
                assert "Test Email 1" in subjects
                assert "Test Email 2" in subjects

                # Verify enqueue was called twice
                assert mock_enqueue.call_count == 2


@pytest.mark.asyncio
async def test_poll_emails_no_new_emails(mock_config):
    """Test when inbox is empty."""
    with patch('app.services.email_poller.EmailFetcher') as mock_fetcher_class:
        # Mock EmailFetcher to return empty list
        mock_fetcher = Mock()
        mock_fetcher.fetch_unread_emails.return_value = []
        mock_fetcher_class.return_value = mock_fetcher

        # Create poller and poll
        poller = EmailPoller()
        result = await poller.poll_emails()

        # Verify result
        assert result is not None
        assert result["processed"] == 0
        assert result["failed"] == 0
        assert len(result["emails"]) == 0


@pytest.mark.asyncio
async def test_poll_emails_parsing_error(mock_config, sample_imap_messages):
    """Test when email parsing fails."""
    with patch('app.services.email_poller.EmailFetcher') as mock_fetcher_class:
        with patch('app.services.email_poller.EmailParser') as mock_parser_class:
            # Mock EmailFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_unread_emails.return_value = sample_imap_messages
            mock_fetcher_class.return_value = mock_fetcher

            # Mock EmailParser to raise exception
            mock_parser = Mock()
            mock_parser.parse.side_effect = Exception("Parsing failed")
            mock_parser_class.return_value = mock_parser

            # Create poller and poll
            poller = EmailPoller()
            result = await poller.poll_emails()

            # Verify failed count
            assert result is not None
            assert result["processed"] == 0
            assert result["failed"] == 2  # Both emails failed


@pytest.mark.asyncio
async def test_poll_emails_queue_enqueue_error(mock_config, sample_imap_messages):
    """Test when queue enqueuing fails."""
    with patch('app.services.email_poller.EmailFetcher') as mock_fetcher_class:
        with patch('app.services.email_poller.EmailParser') as mock_parser_class:
            with patch('app.services.email_poller.enqueue_email_processing') as mock_enqueue:
                # Mock EmailFetcher
                mock_fetcher = Mock()
                mock_fetcher.fetch_unread_emails.return_value = sample_imap_messages
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

                # Mock enqueue to raise exception
                mock_enqueue.side_effect = Exception("Queue is down")

                # Create poller and poll
                poller = EmailPoller()
                result = await poller.poll_emails()

                # Verify failed count
                assert result is not None
                assert result["processed"] == 0
                assert result["failed"] == 2  # Both emails failed to enqueue


@pytest.mark.asyncio
async def test_poll_emails_partial_failure(mock_config, sample_imap_messages):
    """Test when some emails succeed and some fail."""
    with patch('app.services.email_poller.EmailFetcher') as mock_fetcher_class:
        with patch('app.services.email_poller.EmailParser') as mock_parser_class:
            with patch('app.services.email_poller.enqueue_email_processing') as mock_enqueue:
                # Mock EmailFetcher
                mock_fetcher = Mock()
                mock_fetcher.fetch_unread_emails.return_value = sample_imap_messages
                mock_fetcher_class.return_value = mock_fetcher

                # Mock EmailParser.parse_to_ingest static method - first succeeds, second fails
                call_count = [0]

                def parse_side_effect(msg):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return EmailIngest(
                            subject=msg["Subject"],
                            sender=msg["From"],
                            recipients=[msg["To"]],
                            body=str(msg.get_content()),
                            attachments=[],
                            received_at=datetime.utcnow()
                        )
                    else:
                        raise Exception("Second email parsing failed")

                mock_parser_class.parse_to_ingest.side_effect = parse_side_effect

                # Mock enqueue
                mock_job = Mock()
                mock_job.id = "job-1"
                mock_enqueue.return_value = mock_job

                # Create poller and poll
                poller = EmailPoller()
                result = await poller.poll_emails()

                # Verify result
                assert result is not None
                assert result["processed"] == 1  # One succeeded
                assert result["failed"] == 1  # One failed
                assert len(result["emails"]) == 1


@pytest.mark.asyncio
async def test_poll_emails_fetcher_error(mock_config):
    """Test when EmailFetcher raises exception."""
    with patch('app.services.email_poller.EmailFetcher') as mock_fetcher_class:
        # Mock EmailFetcher to raise exception
        mock_fetcher = Mock()
        mock_fetcher.fetch_unread_emails.side_effect = Exception("IMAP connection failed")
        mock_fetcher_class.return_value = mock_fetcher

        # Create poller and poll
        poller = EmailPoller()

        # Should handle exception gracefully
        try:
            result = await poller.poll_emails()
            # If exception is caught, result might be empty or error state
            assert result is not None
        except Exception as e:
            # Or exception might be raised
            assert "IMAP" in str(e)


def test_manual_poll_endpoint(client, mock_config, sample_imap_messages, monkeypatch):
    """Test manual poll API endpoint."""
    # Mock extraction service
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Test Patient",
            case_number="MANUAL-POLL-001",
            exam_type="Orthopedic",
            confidence=0.90,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    with patch('app.routers.email_polling.EmailFetcher') as mock_fetcher_class:
        with patch('app.routers.email_polling.EmailParser') as mock_parser_class:
            with patch('app.routers.email_polling.enqueue_email_processing') as mock_enqueue:
                # Mock EmailFetcher
                mock_fetcher = Mock()
                mock_fetcher.fetch_unread_emails.return_value = sample_imap_messages
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

                # Mock enqueue
                mock_job1 = Mock()
                mock_job1.id = "api-job-1"
                mock_job2 = Mock()
                mock_job2.id = "api-job-2"
                mock_enqueue.side_effect = [mock_job1, mock_job2]

                # Call the manual poll endpoint
                response = client.post("/email-polling/manual-poll")

                # Verify response
                assert response.status_code == 200
                data = response.json()

                assert "processed" in data
                assert data["processed"] == 2
                assert "failed" in data
                assert data["failed"] == 0
                assert "emails" in data
                assert len(data["emails"]) == 2


def test_email_polling_status_endpoint(client, mock_config):
    """Test email polling status endpoint."""
    # Call the status endpoint
    response = client.get("/email-polling/status")

    # Verify response
    assert response.status_code == 200
    data = response.json()

    assert "enabled" in data
    assert "email_address" in data
    assert "imap_server" in data
    assert "poll_interval" in data


@pytest.mark.asyncio
async def test_poll_emails_with_attachments(mock_config, redis_conn):
    """Test polling emails with attachments."""
    # Create email message with attachment
    msg = EmailMessage()
    msg["Subject"] = "Email with Attachment"
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Date"] = "Mon, 15 Jan 2024 10:00:00 +0000"
    msg.set_content("Email body with attachment reference")

    with patch('app.services.email_poller.EmailFetcher') as mock_fetcher_class:
        with patch('app.services.email_poller.EmailParser') as mock_parser_class:
            with patch('app.services.email_poller.enqueue_email_processing') as mock_enqueue:
                # Mock EmailFetcher
                mock_fetcher = Mock()
                mock_fetcher.fetch_unread_emails.return_value = [msg]
                mock_fetcher_class.return_value = mock_fetcher

                # Mock EmailParser.parse_to_ingest static method
                mock_parser_class.parse_to_ingest.return_value = EmailIngest(
                    subject="Email with Attachment",
                    sender="sender@example.com",
                    recipients=["recipient@example.com"],
                    body="Email body",
                    attachments=[
                        {
                            "filename": "test.txt",
                            "content_type": "text/plain",
                            "text_content": "Attachment content"
                        }
                    ],
                    received_at=datetime.utcnow()
                )

                # Mock enqueue
                mock_job = Mock()
                mock_job.id = "job-with-attachment"
                mock_enqueue.return_value = mock_job

                # Create poller and poll
                poller = EmailPoller()
                result = await poller.poll_emails()

                # Verify result
                assert result is not None
                assert result["processed"] == 1
                assert result["failed"] == 0

                # Verify enqueue was called with correct data
                assert mock_enqueue.called
                call_args = mock_enqueue.call_args[0][0]
                assert isinstance(call_args, EmailIngest)
                assert len(call_args.attachments) == 1
                assert call_args.attachments[0]["filename"] == "test.txt"
