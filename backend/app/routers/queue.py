"""
Queue management and monitoring endpoints.
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from app.services.queue import (
    get_queue_stats,
    get_all_queue_stats,
    get_job_status,
    get_redis_connection
)

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/status")
def get_queue_status() -> Dict[str, Any]:
    """
    Get status and statistics for all queues.

    Returns queue counts, worker counts, and Redis connection status.
    """
    try:
        # Test Redis connection
        redis_conn = get_redis_connection()
        redis_conn.ping()

        # Get stats for all queues
        stats = get_all_queue_stats()

        return {
            "redis_connected": True,
            "queues": stats
        }

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
