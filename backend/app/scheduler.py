"""
RQ Scheduler entry point for handling retry jobs.

The WindowsWorker doesn't process scheduled jobs (retries) automatically.
This separate scheduler process moves retry jobs from the scheduled registry
back to the queue when they're ready to run.

Usage:
    python -m app.scheduler

Run this ALONGSIDE the worker process (in a separate terminal).
"""
import sys
import time
import logging
from rq import Queue
from rq.registry import ScheduledJobRegistry

from app.config import settings
from app.services.queue import get_redis_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def process_scheduled_jobs(queue_names: list[str], redis_conn):
    """
    Check scheduled job registries and enqueue jobs that are ready.

    Args:
        queue_names: List of queue names to monitor
        redis_conn: Redis connection
    """
    from rq.job import Job

    total_enqueued = 0

    for queue_name in queue_names:
        try:
            queue = Queue(queue_name, connection=redis_conn)
            registry = ScheduledJobRegistry(queue=queue)

            # Get count of scheduled jobs
            count = registry.count

            if count > 0:
                # Manually check each scheduled job and enqueue if ready
                from datetime import datetime, timezone

                current_time = datetime.now(timezone.utc)
                job_ids = registry.get_job_ids()

                for job_id in job_ids:
                    try:
                        scheduled_time = registry.get_scheduled_time(job_id)

                        # If scheduled time is None or has passed, enqueue it
                        if scheduled_time is None or scheduled_time <= current_time:
                            # Remove from scheduled registry
                            registry.remove(job_id)

                            # Add to queue
                            job = Job.fetch(job_id, connection=redis_conn)
                            queue.enqueue_job(job)

                            total_enqueued += 1
                            logger.info(f"[{queue_name}] Enqueued job {job_id}")
                    except Exception as e:
                        logger.warning(f"Error processing job {job_id}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error processing {queue_name} queue: {e}")
            import traceback
            traceback.print_exc()

    return total_enqueued


def main():
    """
    Start the retry job scheduler.

    Continuously monitors scheduled job registries and moves ready jobs
    back to their queues for processing. This handles RQ's retry mechanism.
    """
    logger.info("Starting RQ Retry Scheduler...")
    logger.info(f"Redis URL: {settings.REDIS_URL}")

    # Get Redis connection
    redis_conn = get_redis_connection()

    # Queue names to monitor
    queue_names = ["high", "default", "low"]

    logger.info(f"Monitoring queues: {', '.join(queue_names)}")
    logger.info("Scheduler ready. Processing retry jobs...")
    logger.info("Checking every 1 second for scheduled jobs to enqueue.")
    logger.info("Press Ctrl+C to stop.")
    logger.info("")

    # Main loop
    try:
        while True:
            enqueued = process_scheduled_jobs(queue_names, redis_conn)

            # Sleep for 1 second before next check
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
