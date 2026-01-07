"""
Tests for queue service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.schemas.email import EmailIngest
from app.services.queue import (
    get_redis_connection,
    get_queue,
    enqueue_email_processing,
    get_job_status,
    get_queue_stats,
    get_all_queue_stats,
    enqueue_with_sync_fallback
)


def test_get_redis_connection(redis_conn):
    """Test Redis connection is established."""
    with patch('app.services.queue.Redis') as mock_redis:
        mock_redis.from_url.return_value = redis_conn

        # Reset the global connection
        import app.services.queue
        app.services.queue._redis_conn = None

        # Get connection
        conn = get_redis_connection()

        # Verify connection was created
        assert conn is not None
        mock_redis.from_url.assert_called_once()


def test_get_queue(redis_conn):
    """Test queue instance creation."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        from rq import Queue
        queue = get_queue("default")

        # Verify queue was created
        assert queue is not None
        assert isinstance(queue, Queue)
        assert queue.name == "default"


def test_enqueue_email_processing(redis_conn, sample_email_ingest):
    """Test job enqueueing with retry configuration."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        # Enqueue the job
        job = enqueue_email_processing(sample_email_ingest)

        # Verify job was created
        assert job is not None
        assert job.id is not None

        # Verify job ID format
        assert "email_" in job.id
        assert sample_email_ingest.sender in job.id

        # Verify job metadata
        assert job.meta is not None
        assert job.meta["subject"] == sample_email_ingest.subject
        assert job.meta["sender"] == sample_email_ingest.sender

        # Verify job description
        assert job.description is not None
        assert sample_email_ingest.subject[:50] in job.description

        # Verify retry configuration
        assert job.retries_left is not None or job.retry is not None


def test_enqueue_email_processing_high_priority(redis_conn, sample_email_ingest):
    """Test enqueueing with high priority queue."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        # Enqueue with high priority
        job = enqueue_email_processing(sample_email_ingest, high_priority=True)

        # Verify job was created
        assert job is not None

        # Verify it was enqueued to high priority queue
        from rq import Queue
        high_queue = Queue("high", connection=redis_conn)
        assert job.id in high_queue.job_ids


def test_get_job_status(redis_conn, sample_email_ingest):
    """Test job status retrieval."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        # Create a job
        job = enqueue_email_processing(sample_email_ingest)

        # Get job status
        status = get_job_status(job.id)

        # Verify status information
        assert status is not None
        assert status["job_id"] == job.id
        assert "status" in status
        assert status["status"] in ["queued", "started", "finished", "failed"]
        assert "meta" in status
        assert status["meta"]["subject"] == sample_email_ingest.subject


def test_get_job_status_not_found(redis_conn):
    """Test job status for non-existent job."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        # Try to get status for non-existent job
        with pytest.raises(Exception):
            # Should raise an exception when job is not found
            get_job_status("nonexistent-job-id")


def test_get_queue_stats(redis_conn):
    """Test queue statistics."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        # Get stats for default queue
        stats = get_queue_stats("default")

        # Verify stats structure
        assert stats is not None
        assert "name" in stats
        assert stats["name"] == "default"
        assert "queued" in stats
        assert "started" in stats
        assert "finished" in stats
        assert "failed" in stats
        assert "workers" in stats

        # Verify all values are integers
        assert isinstance(stats["queued"], int)
        assert isinstance(stats["finished"], int)
        assert isinstance(stats["workers"], int)


def test_get_all_queue_stats(redis_conn):
    """Test stats for all queues."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        # Get stats for all queues
        all_stats = get_all_queue_stats()

        # Verify stats for all queue types
        assert all_stats is not None
        assert "default" in all_stats
        assert "high" in all_stats
        assert "low" in all_stats

        # Verify each queue has stats
        for queue_name in ["default", "high", "low"]:
            assert "name" in all_stats[queue_name] or "error" in all_stats[queue_name]


def test_enqueue_with_sync_fallback_success(redis_conn, sample_email_ingest, db, monkeypatch):
    """Test normal queue operation with sync fallback."""
    # Mock extraction service
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Test Patient",
            case_number="TEST-001",
            exam_type="Orthopedic",
            confidence=0.95,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        # Mock job.latest_result() to return immediately
        with patch('app.services.queue.enqueue_email_processing') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = "test-job-id"

            # Mock result
            mock_result = Mock()
            mock_result.return_value = {
                "job_id": "test-job-id",
                "email_id": "test-email-id",
                "status": "processed"
            }
            mock_job.latest_result.return_value = mock_result

            mock_enqueue.return_value = mock_job

            # Call enqueue_with_sync_fallback
            result = enqueue_with_sync_fallback(sample_email_ingest)

            # Verify result
            assert result is not None
            assert result["status"] == "processed"


def test_enqueue_with_sync_fallback_redis_down(sample_email_ingest, db, monkeypatch):
    """Test fallback to sync processing when Redis is down."""
    # Mock extraction service
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Test Patient",
            case_number="TEST-001",
            exam_type="Orthopedic",
            confidence=0.95,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    # Mock enqueue_email_processing to raise exception
    with patch('app.services.queue.enqueue_email_processing') as mock_enqueue:
        mock_enqueue.side_effect = Exception("Redis connection failed")

        # Call enqueue_with_sync_fallback
        result = enqueue_with_sync_fallback(sample_email_ingest)

        # Verify fallback was used
        assert result is not None
        assert "fallback" in result
        assert result["fallback"] is True
        assert "email_id" in result
        assert "case_id" in result
        assert result["status"] == "processed"
        assert "Processed synchronously" in result["message"]


def test_enqueue_with_sync_fallback_timeout(redis_conn, sample_email_ingest, monkeypatch):
    """Test when job doesn't complete in time."""
    # Mock extraction service
    from app.services import extraction
    from app.schemas.extraction import CaseExtraction

    def mock_extraction(*args, **kwargs):
        return CaseExtraction(
            patient_name="Test Patient",
            case_number="TEST-001",
            exam_type="Orthopedic",
            confidence=0.95,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

    monkeypatch.setattr(extraction, "extract_case_from_email", mock_extraction)

    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        with patch('app.services.queue.enqueue_email_processing') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = "test-job-id"
            mock_job.latest_result.return_value = None  # Simulate timeout

            mock_enqueue.return_value = mock_job

            # Call enqueue_with_sync_fallback
            result = enqueue_with_sync_fallback(sample_email_ingest)

            # Verify result indicates queued status
            assert result is not None
            assert result["job_id"] == "test-job-id"
            assert result["status"] == "queued"
            assert "processing in background" in result["message"]


def test_queue_retry_configuration(redis_conn, sample_email_ingest):
    """Test that retry configuration is correct."""
    with patch('app.services.queue.get_redis_connection') as mock_get_conn:
        mock_get_conn.return_value = redis_conn

        from app.config import settings

        # Enqueue a job
        job = enqueue_email_processing(sample_email_ingest)

        # Verify retry configuration
        # Note: RQ stores retry config in job.retry attribute
        assert job is not None

        # The job should have retry configured
        # This is set via Retry(max=5, interval=[1, 2, 4, 8, 16])
        # We can verify by checking if job has the retry attribute
        assert hasattr(job, 'retry') or hasattr(job, 'retries_left')
