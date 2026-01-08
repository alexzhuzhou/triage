"""
RQ Worker entry point using SimpleWorker.

SimpleWorker processes jobs in the main thread without forking or spawning,
making it fully compatible with Windows.

Usage:
    python -m app.worker

Environment variables are loaded from .env file.
"""
import sys
import os
import logging
import threading
from rq import SimpleWorker
from rq.logutils import setup_loghandlers
from fastapi import FastAPI
import uvicorn

from app.config import settings
from app.services.queue import get_redis_connection

# Health check app for Cloud Run (requires HTTP endpoint)
health_app = FastAPI()


@health_app.get("/health")
def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "worker": "running", "service": "triage-worker"}


def run_health_server():
    """Run health check HTTP server in background thread."""
    port = int(os.environ.get("PORT", 8080))
    logger = logging.getLogger(__name__)
    logger.info(f"Starting health check server on port {port}")
    uvicorn.run(health_app, host="0.0.0.0", port=port, log_level="warning")

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
    Start the RQ worker using SimpleWorker with health check server.
    """
    logger.info("Starting RQ Worker...")
    logger.info(f"Redis URL: {settings.REDIS_URL}")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Max retries: {settings.QUEUE_RETRY_ATTEMPTS}")

    # Start health check server in background thread (for Cloud Run)
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health check server started in background thread")

    # Get Redis connection
    redis_conn = get_redis_connection()

    # Parse queue names from command line args or use defaults
    queue_names = sys.argv[1:] if len(sys.argv) > 1 else ["default"]

    logger.info(f"Listening on queues: {', '.join(queue_names)}")

    # Use SimpleWorker for Windows compatibility
    logger.info("Using SimpleWorker (fully compatible with Windows)")
    worker = SimpleWorker(
        queue_names,
        connection=redis_conn,
        name=f"worker-{settings.ENV}",
        log_job_description=True
    )

    # Setup RQ log handlers
    setup_loghandlers(level=logging.INFO)

    # Start processing jobs
    logger.info("Worker ready. Waiting for jobs...")
    logger.info("")

    # SimpleWorker handles retries automatically
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
