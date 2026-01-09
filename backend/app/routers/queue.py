"""
Queue monitoring and management endpoints.
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from rq import Queue, Worker
from rq.job import Job
from rq.registry import (
    StartedJobRegistry,
    FinishedJobRegistry,
    FailedJobRegistry,
    ScheduledJobRegistry,
    DeferredJobRegistry
)

from app.services.queue import get_redis_connection, get_queue

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/status")
def get_queue_status() -> Dict[str, Any]:
    """
    Get comprehensive queue status including all registries.

    Returns counts for:
    - queued: Jobs waiting to be processed
    - started: Jobs currently being processed
    - finished: Successfully completed jobs
    - failed: Jobs that failed after all retries
    - scheduled: Jobs scheduled for future execution (retries)
    - deferred: Jobs waiting for dependencies
    """
    try:
        redis_conn = get_redis_connection()
        queue = get_queue("default")

        # Get all registries
        started_registry = StartedJobRegistry(queue=queue)
        finished_registry = FinishedJobRegistry(queue=queue)
        failed_registry = FailedJobRegistry(queue=queue)
        scheduled_registry = ScheduledJobRegistry(queue=queue)
        deferred_registry = DeferredJobRegistry(queue=queue)

        # Get workers from Redis connection
        workers = Worker.all(connection=redis_conn)

        return {
            "queue": "default",
            "counts": {
                "queued": len(queue),
                "started": len(started_registry),
                "finished": len(finished_registry),
                "failed": len(failed_registry),
                "scheduled": len(scheduled_registry),
                "deferred": len(deferred_registry)
            },
            "is_empty": queue.is_empty(),
            "worker_count": len(workers),
            "total_jobs": (
                len(queue) +
                len(started_registry) +
                len(finished_registry) +
                len(failed_registry) +
                len(scheduled_registry) +
                len(deferred_registry)
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


@router.get("/jobs/{job_id}")
def get_job_details(job_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific job.

    Args:
        job_id: The job ID to lookup

    Returns:
        Job details including status, timestamps, result, and error info
    """
    try:
        redis_conn = get_redis_connection()
        job = Job.fetch(job_id, connection=redis_conn)

        return {
            "job_id": job.id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": job.result,
            "exc_info": job.exc_info,
            "meta": job.meta,
            "description": job.description,
            "retry_attempts": job.retries_left if hasattr(job, 'retries_left') else None
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {str(e)}")


@router.get("/failed-jobs")
def list_failed_jobs(limit: int = 100) -> Dict[str, Any]:
    """
    List all failed jobs in the queue.

    Args:
        limit: Maximum number of jobs to return (default: 100)

    Returns:
        List of failed job details
    """
    try:
        redis_conn = get_redis_connection()
        queue = get_queue("default")
        failed_registry = FailedJobRegistry(queue=queue)

        failed_job_ids = failed_registry.get_job_ids(0, limit - 1)
        failed_jobs = []

        for job_id in failed_job_ids:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                failed_jobs.append({
                    "job_id": job.id,
                    "description": job.description,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "failed_at": job.ended_at.isoformat() if job.ended_at else None,
                    "error": str(job.exc_info) if job.exc_info else None,
                    "meta": job.meta
                })
            except Exception:
                # Job might have been deleted, skip it
                continue

        return {
            "total_failed": len(failed_registry),
            "returned": len(failed_jobs),
            "jobs": failed_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list failed jobs: {str(e)}")


@router.post("/cleanup")
def cleanup_finished_jobs() -> Dict[str, Any]:
    """
    Clean up finished and failed jobs from the queue registries.

    This helps prevent registry buildup over time. It's safe to call periodically.

    Returns:
        Counts of cleaned up jobs
    """
    try:
        redis_conn = get_redis_connection()
        queue = get_queue("default")

        finished_registry = FinishedJobRegistry(queue=queue)
        failed_registry = FailedJobRegistry(queue=queue)

        # Get counts before cleanup
        finished_count = len(finished_registry)
        failed_count = len(failed_registry)

        # Clean up old finished jobs (older than 1 hour)
        finished_registry.cleanup(1 * 60 * 60)  # 1 hour in seconds

        # Don't auto-cleanup failed jobs - user might want to inspect them
        # But we can provide manual cleanup if needed

        return {
            "cleaned": {
                "finished": finished_count,
                "failed": 0  # Don't auto-cleanup failed
            },
            "remaining": {
                "finished": len(finished_registry),
                "failed": len(failed_registry)
            },
            "message": "Finished jobs older than 1 hour have been cleaned up. Failed jobs retained for inspection."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup jobs: {str(e)}")


@router.get("/health")
def queue_health() -> Dict[str, Any]:
    """
    Check if the queue system is healthy.

    Returns:
        Health status including Redis connectivity and worker availability
    """
    try:
        redis_conn = get_redis_connection()
        queue = get_queue("default")

        # Check Redis connection
        redis_conn.ping()

        # Check for active workers using Worker.all()
        workers = Worker.all(connection=redis_conn)

        is_healthy = len(workers) > 0

        return {
            "status": "healthy" if is_healthy else "degraded",
            "redis_connected": True,
            "worker_count": len(workers),
            "workers": [w.name for w in workers],
            "message": "Queue is operational" if is_healthy else "No workers available - jobs won't be processed"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis_connected": False,
            "worker_count": 0,
            "workers": [],
            "error": str(e),
            "message": "Cannot connect to Redis or queue system"
        }


@router.post("/admin/clear-workers")
def clear_worker_registrations() -> Dict[str, Any]:
    """
    ADMIN: Clear all worker registrations from Redis.

    Use this before redeploying workers to avoid "worker already exists" errors.
    This is safe to call - workers will re-register when they start.

    Returns:
        Counts of cleared registrations
    """
    try:
        redis_conn = get_redis_connection()

        # Get all worker keys
        worker_keys = redis_conn.keys("rq:worker:*")

        # Delete worker keys
        deleted_workers = 0
        if worker_keys:
            deleted_workers = redis_conn.delete(*worker_keys)

        # Clear workers set
        workers_set = redis_conn.smembers("rq:workers")
        cleared_set = False
        if workers_set:
            redis_conn.delete("rq:workers")
            cleared_set = True

        return {
            "success": True,
            "deleted_worker_keys": deleted_workers,
            "cleared_workers_set": cleared_set,
            "message": "Worker registrations cleared. You can now redeploy the worker service."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear workers: {str(e)}")
