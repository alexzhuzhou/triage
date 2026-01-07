"""
RQ Worker entry point.

Run this script to start a background worker that processes queued jobs.

Usage:
    python -m app.worker

Or with specific queues:
    python -m app.worker --queues high default low

Environment variables are loaded from .env file.
"""
import sys
import os
import logging
from rq import Worker
from rq.logutils import setup_loghandlers

from app.config import settings
from app.services.queue import get_redis_connection

# Import Windows-compatible worker if on Windows
if os.name == 'nt':
    try:
        from rq_win import WindowsWorker
    except ImportError:
        WindowsWorker = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """
    Start the RQ worker.
    """
    logger.info("Starting RQ worker...")
    logger.info(f"Redis URL: {settings.REDIS_URL}")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Max retries: {settings.QUEUE_RETRY_ATTEMPTS}")

    # Get Redis connection
    redis_conn = get_redis_connection()

    # Parse queue names from command line args or use defaults
    queue_names = sys.argv[1:] if len(sys.argv) > 1 else ["high", "default", "low"]

    logger.info(f"Listening on queues: {', '.join(queue_names)}")

    # Detect Windows and use WindowsWorker from rq-win
    is_windows = os.name == 'nt'

    if is_windows:
        if WindowsWorker is None:
            logger.error("Running on Windows but rq-win is not installed!")
            logger.error("Install it with: pip install rq-win")
            sys.exit(1)

        logger.info("Detected Windows - using WindowsWorker from rq-win")
        worker = WindowsWorker(
            queue_names,
            connection=redis_conn,
            name=f"worker-{settings.ENV}",
            log_job_description=True
        )
    else:
        # On Unix/Linux, use regular Worker
        logger.info("Detected Unix/Linux - using standard RQ Worker")
        worker = Worker(
            queue_names,
            connection=redis_conn,
            name=f"worker-{settings.ENV}",
            log_job_description=True,
            disable_default_exception_handler=False
        )

    # Setup RQ log handlers
    setup_loghandlers(level=logging.INFO)

    # Start processing jobs
    logger.info("Worker ready. Waiting for jobs...")
    logger.info("")
    logger.info("=" * 70)
    logger.info("IMPORTANT: For automatic retries, run the scheduler separately:")
    logger.info("  python -m app.scheduler")
    logger.info("=" * 70)
    logger.info("")

    # WindowsWorker's with_scheduler doesn't work reliably - use separate scheduler
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
