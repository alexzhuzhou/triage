"""
Temporary script to clear Redis worker registration.
Run this before redeploying the worker.
"""
from app.services.queue import get_redis_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_worker_registration():
    """Clear all worker registrations from Redis."""
    try:
        redis_conn = get_redis_connection()

        # Get all worker keys
        worker_keys = redis_conn.keys("rq:worker:*")
        logger.info(f"Found {len(worker_keys)} worker keys: {worker_keys}")

        # Delete worker keys
        if worker_keys:
            deleted = redis_conn.delete(*worker_keys)
            logger.info(f"Deleted {deleted} worker keys")

        # Clear workers set
        workers_set = redis_conn.smembers("rq:workers")
        if workers_set:
            logger.info(f"Workers in set: {workers_set}")
            redis_conn.delete("rq:workers")
            logger.info("Cleared workers set")

        # Clear worker heartbeats
        heartbeat_keys = redis_conn.keys("rq:worker:*:heartbeat")
        if heartbeat_keys:
            redis_conn.delete(*heartbeat_keys)
            logger.info(f"Cleared {len(heartbeat_keys)} heartbeat keys")

        logger.info("✅ Worker registration cleared successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Error clearing worker registration: {e}")
        return False

if __name__ == "__main__":
    clear_worker_registration()
