"""
Queue management service using RQ (Redis Queue).

Provides functions to enqueue jobs and check job status.
"""
import logging
from typing import Dict, Any, Optional
from redis import Redis
from rq import Queue, Retry, Worker
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
        name: Queue name (default, high, low, etc.)

    Returns:
        Queue: RQ queue instance
    """
    redis_conn = get_redis_connection()
    return Queue(name, connection=redis_conn, default_timeout=settings.QUEUE_DEFAULT_TIMEOUT)


def enqueue_email_processing(
    email_data: EmailIngest,
    queue_name: str = "default",
    high_priority: bool = False
) -> Job:
    """
    Enqueue an email for background processing with retry logic.

    Args:
        email_data: Email data to process
        queue_name: Queue name to use
        high_priority: If True, use high-priority queue

    Returns:
        Job: RQ job instance
    """
    queue = get_queue("high" if high_priority else queue_name)

    # Convert Pydantic model to dict for Redis serialization
    email_dict = email_data.model_dump(mode="json")

    # Exponential backoff: 1s, 2s, 4s, 8s, 16s (total ~31s + job time)
    retry = Retry(max=settings.QUEUE_RETRY_ATTEMPTS, interval=[1, 2, 4, 8, 16])

    job = queue.enqueue(
        "app.tasks.process_email_task",
        email_dict,
        retry=retry,
        job_id=f"email_{email_data.sender}_{email_data.subject[:20]}_{id(email_data)}",
        description=f"Process email: {email_data.subject[:50]}",
        meta={
            "subject": email_data.subject,
            "sender": email_data.sender,
            "enqueued_at": email_data.received_at.isoformat() if email_data.received_at else None
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
    job = Job.fetch(job_id, connection=redis_conn)

    if not job:
        return {"error": "Job not found"}

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


def cleanup_finished_jobs(queue_name: str = "default") -> int:
    """
    Clean up jobs that are finished but stuck in the started registry.
    This is a workaround for rq-win on Windows which doesn't properly move
    finished jobs to the finished registry.

    Args:
        queue_name: Queue name to clean up

    Returns:
        Number of jobs moved to finished registry
    """
    from rq.job import Job

    queue = get_queue(queue_name)
    redis_conn = get_redis_connection()
    started_registry = queue.started_job_registry
    finished_registry = queue.finished_job_registry

    moved_count = 0
    for job_id in list(started_registry.get_job_ids()):
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            if job.get_status() == 'finished':
                # Move from started to finished registry
                started_registry.remove(job)
                finished_registry.add(job, -1)  # -1 means don't set TTL
                moved_count += 1
                logger.debug(f"Moved finished job {job_id} to finished registry")
        except Exception as e:
            logger.warning(f"Error cleaning up job {job_id}: {e}")

    if moved_count > 0:
        logger.info(f"Cleaned up {moved_count} finished jobs in {queue_name} queue")

    return moved_count


def get_queue_stats(queue_name: str = "default", cleanup: bool = False) -> Dict[str, Any]:
    """
    Get statistics about a queue.

    Args:
        queue_name: Queue name to check
        cleanup: If True, clean up finished jobs stuck in started registry (Windows fix)

    Returns:
        Dict with queue statistics
    """
    queue = get_queue(queue_name)
    redis_conn = get_redis_connection()

    # Clean up finished jobs if requested (Windows rq-win workaround)
    cleaned = 0
    if cleanup:
        cleaned = cleanup_finished_jobs(queue_name)

    # Get registry counts
    started_registry = queue.started_job_registry
    finished_registry = queue.finished_job_registry
    failed_registry = queue.failed_job_registry
    deferred_registry = queue.deferred_job_registry
    scheduled_registry = queue.scheduled_job_registry

    # Get workers that are listening to this queue
    all_workers = Worker.all(connection=redis_conn)
    workers_on_queue = [w for w in all_workers if queue_name in w.queue_names()]

    return {
        "name": queue_name,
        "queued": len(queue),
        "started": len(started_registry),
        "finished": len(finished_registry),
        "failed": len(failed_registry),
        "deferred": len(deferred_registry),
        "scheduled": len(scheduled_registry),
        "workers": len(workers_on_queue),
        "cleaned_up": cleaned if cleanup else None
    }


def get_all_queue_stats() -> Dict[str, Any]:
    """
    Get statistics for all queues.

    Returns:
        Dict with stats for all queues
    """
    queue_names = ["default", "high", "low"]
    stats = {}

    for name in queue_names:
        try:
            stats[name] = get_queue_stats(name)
        except Exception as e:
            logger.error(f"Failed to get stats for queue {name}: {e}")
            stats[name] = {"error": str(e)}

    return stats


def enqueue_with_sync_fallback(email_data: EmailIngest) -> Dict[str, Any]:
    """
    Try to enqueue a job, but fall back to synchronous processing if Redis is down.

    This ensures the API remains available even if Redis fails.

    Args:
        email_data: Email data to process

    Returns:
        Dict with processing results
    """
    try:
        # Try to enqueue
        job = enqueue_email_processing(email_data)

        # Wait for result (synchronous behavior for API endpoint)
        result = job.latest_result(timeout=settings.QUEUE_DEFAULT_TIMEOUT)

        if result:
            return result.return_value
        else:
            # Job didn't complete in time
            return {
                "job_id": job.id,
                "status": "queued",
                "message": "Job is processing in background"
            }

    except Exception as e:
        logger.warning(f"Queue unavailable, falling back to synchronous processing: {e}")

        # Fall back to direct processing
        from app.database import SessionLocal
        from app.services.ingestion import process_email as sync_process_email

        db = SessionLocal()
        try:
            email = sync_process_email(db, email_data)
            return {
                "email_id": str(email.id),
                "case_id": str(email.case_id) if email.case_id else None,
                "status": email.processing_status.value,
                "fallback": True,
                "message": "Processed synchronously (queue unavailable)"
            }
        finally:
            db.close()
