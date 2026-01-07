"""
Queue management service using RQ (Redis Queue).

Provides functions to enqueue jobs with retry logic.
"""
import logging
import hashlib
from typing import Dict, Any
from redis import Redis
from rq import Queue, Retry
from rq.job import Job

from app.config import settings
from app.schemas.email import EmailIngest

logger = logging.getLogger(__name__)


# Redis connection (shared across the application)
_redis_conn = None


def get_redis_connection() -> Redis:
    """
    Get or create a Redis connection.

    Returns:
        Redis: Redis connection instance
    """
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=False  # Keep binary for RQ compatibility
        )
        logger.info(f"Connected to Redis at {settings.REDIS_URL}")
    return _redis_conn


def get_queue(name: str = "default") -> Queue:
    """
    Get an RQ queue instance.

    Args:
        name: Queue name (default is "default")

    Returns:
        Queue: RQ queue instance
    """
    redis_conn = get_redis_connection()
    return Queue(name, connection=redis_conn, default_timeout=settings.QUEUE_DEFAULT_TIMEOUT)


def enqueue_email_processing(email_data: EmailIngest) -> Job:
    """
    Enqueue an email for background processing with retry logic.

    Uses deterministic job IDs based on email identity (sender, subject, received_at)
    to prevent duplicate jobs for the same email. If the same email is enqueued
    multiple times (auto-retry + manual retry), only one job will exist in the queue.

    Args:
        email_data: Email data to process

    Returns:
        Job: RQ job instance (existing job if already queued, new job otherwise)
    """
    queue = get_queue("default")
    redis_conn = get_redis_connection()

    # Convert Pydantic model to dict for Redis serialization
    email_dict = email_data.model_dump(mode="json")

    # Generate deterministic job ID based on email identity
    # Same email = same job_id = prevents duplicates
    received_at_str = email_data.received_at.isoformat() if email_data.received_at else ""
    identity_string = f"{email_data.sender}|{email_data.subject}|{received_at_str}"
    job_hash = hashlib.sha256(identity_string.encode()).hexdigest()[:16]
    job_id = f"email_{job_hash}"

    # Check if job already exists and is active (queued, started, deferred, scheduled)
    try:
        existing_job = Job.fetch(job_id, connection=redis_conn)
        job_status = existing_job.get_status()

        if job_status in ['queued', 'started', 'deferred', 'scheduled']:
            logger.info(f"Job {job_id} already exists with status '{job_status}', returning existing job")
            return existing_job

        # If job is finished or failed, we can create a new one with same ID
        # Delete the old job first to free up the job_id
        logger.info(f"Deleting old job {job_id} with status '{job_status}' before re-enqueueing")
        existing_job.delete()
    except Exception:
        # Job doesn't exist, that's fine - we'll create it
        pass

    # Exponential backoff: 1s, 2s, 4s, 8s, 16s (total ~31s + job time)
    retry = Retry(max=settings.QUEUE_RETRY_ATTEMPTS, interval=[1, 2, 4, 8, 16])

    job = queue.enqueue(
        "app.tasks.process_email_task",
        email_dict,
        retry=retry,
        job_id=job_id,
        description=f"Process email: {email_data.subject[:50]}",
        meta={
            "subject": email_data.subject,
            "sender": email_data.sender,
            "enqueued_at": received_at_str
        }
    )

    logger.info(f"Enqueued email processing job: {job.id}")
    return job


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a queued job.

    Args:
        job_id: Job ID to check

    Returns:
        Dict with job status information
    """
    redis_conn = get_redis_connection()

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception as e:
        return {"error": f"Job not found: {str(e)}"}

    return {
        "job_id": job.id,
        "status": job.get_status(),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        "result": job.result,
        "exc_info": job.exc_info,
        "meta": job.meta,
        "description": job.description
    }
