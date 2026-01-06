"""
Background tasks for RQ (Redis Queue).

These tasks are executed by worker processes and include retry logic
for handling transient failures (OpenAI API timeouts, rate limits, etc.).
"""
import logging
from datetime import datetime
from typing import Dict, Any
from rq import get_current_job
from rq.job import Job

from app.database import SessionLocal
from app.schemas.email import EmailIngest
from app.services.ingestion import process_email as sync_process_email

logger = logging.getLogger(__name__)


def process_email_task(email_data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task to process an email through the LLM extraction pipeline.

    This task is retried automatically by RQ on failure (up to 5 times with
    exponential backoff).

    Args:
        email_data_dict: Email data as dictionary (serializable for Redis)

    Returns:
        Dict with processing results (email_id, case_id, status)

    Raises:
        Exception: If processing fails after all retries
    """
    job = get_current_job()
    job_id = job.id if job else "unknown"

    logger.info(f"[Job {job_id}] Starting email processing task")
    logger.info(f"[Job {job_id}] Email subject: {email_data_dict.get('subject', 'N/A')}")

    db = SessionLocal()
    try:
        # Convert dict back to Pydantic model
        email_data = EmailIngest(**email_data_dict)

        # Process email through ingestion pipeline
        email = sync_process_email(db, email_data)

        result = {
            "job_id": job_id,
            "email_id": str(email.id),
            "case_id": str(email.case_id) if email.case_id else None,
            "status": email.processing_status.value,
            "subject": email.subject,
            "processed_at": email.processed_at.isoformat() if email.processed_at else None
        }

        logger.info(f"[Job {job_id}] Successfully processed email: {email.id}")
        return result

    except Exception as e:
        logger.error(f"[Job {job_id}] Failed to process email: {str(e)}")

        # Log retry information if available
        if job:
            retry_count = job.retries_left if hasattr(job, 'retries_left') else 0
            logger.warning(f"[Job {job_id}] Retries left: {retry_count}")

        raise  # Re-raise to trigger RQ retry mechanism

    finally:
        db.close()
