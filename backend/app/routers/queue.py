"""
Queue management and monitoring endpoints.
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from app.services.queue import (
    get_queue_stats,
    get_all_queue_stats,
    get_job_status,
    get_redis_connection,
    cleanup_finished_jobs
)

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/status")
def get_queue_status(cleanup: bool = False) -> Dict[str, Any]:
    """
    Get status and statistics for all queues.

    Args:
        cleanup: If True, clean up finished jobs stuck in started registry (Windows fix)

    Returns queue counts, worker counts, and Redis connection status.
    """
    try:
        # Test Redis connection
        redis_conn = get_redis_connection()
        redis_conn.ping()

        # Clean up finished jobs if requested (Windows rq-win workaround)
        cleaned_total = 0
        if cleanup:
            for queue_name in ["default", "high", "low"]:
                cleaned_total += cleanup_finished_jobs(queue_name)

        # Get stats for all queues
        stats = get_all_queue_stats()

        response = {
            "redis_connected": True,
            "queues": stats
        }

        if cleanup:
            response["cleaned_up_jobs"] = cleaned_total

        return response

    except Exception as e:
        return {
            "redis_connected": False,
            "error": str(e),
            "queues": {}
        }


@router.get("/stats/{queue_name}")
def get_specific_queue_stats(queue_name: str) -> Dict[str, Any]:
    """
    Get detailed statistics for a specific queue.

    Args:
        queue_name: Name of the queue (default, high, low)

    Returns:
        Dict with queue statistics
    """
    try:
        stats = get_queue_stats(queue_name)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


@router.get("/jobs/{job_id}")
def get_job_details(job_id: str) -> Dict[str, Any]:
    """
    Get details and status of a specific job.

    Args:
        job_id: Job ID to check

    Returns:
        Dict with job information
    """
    try:
        job_info = get_job_status(job_id)

        if "error" in job_info:
            raise HTTPException(status_code=404, detail=job_info["error"])

        return job_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/cleanup")
def cleanup_queue_registries() -> Dict[str, Any]:
    """
    Clean up finished jobs stuck in started registry.

    This is a workaround for rq-win on Windows which doesn't properly move
    finished jobs to the finished registry. This endpoint moves all finished
    jobs from the started registry to the finished registry.

    Returns:
        Dict with cleanup statistics
    """
    try:
        cleaned_jobs = {}
        total_cleaned = 0

        for queue_name in ["default", "high", "low"]:
            count = cleanup_finished_jobs(queue_name)
            cleaned_jobs[queue_name] = count
            total_cleaned += count

        return {
            "success": True,
            "total_cleaned": total_cleaned,
            "by_queue": cleaned_jobs,
            "message": f"Cleaned up {total_cleaned} finished jobs"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clean up jobs: {str(e)}")


@router.get("/health")
def queue_health_check() -> Dict[str, Any]:
    """
    Health check for queue system.

    Checks Redis connectivity and worker availability.
    """
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()

        stats = get_all_queue_stats()

        # Check if any workers are available
        total_workers = sum(q.get("workers", 0) for q in stats.values() if isinstance(q, dict))

        return {
            "status": "healthy",
            "redis_connected": True,
            "workers_available": total_workers,
            "warning": "No workers available" if total_workers == 0 else None
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "redis_connected": False,
            "error": str(e)
        }
