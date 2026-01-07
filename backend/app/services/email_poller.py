"""
Email poller service for background email fetching.

Runs as a background task to periodically check for new emails
and enqueue them for processing.
"""
import asyncio
import logging
from typing import Dict, Any

from app.config import settings
from app.services.email_fetcher import EmailFetcher
from app.services.email_parser import EmailParser
from app.services.queue import enqueue_email_processing

logger = logging.getLogger(__name__)


class EmailPoller:
    """Background email polling service."""

    def __init__(self):
        self.is_running = False
        self.poll_count = 0

    async def start(self):
        """Start the email polling loop."""
        if not settings.EMAIL_ENABLED:
            logger.info("Email polling is disabled (EMAIL_ENABLED=false)")
            return

        if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
            logger.warning("Email credentials not configured. Skipping email polling.")
            return

        logger.info(f"Starting email poller (interval: {settings.EMAIL_POLL_INTERVAL}s)")
        self.is_running = True

        while self.is_running:
            try:
                await self.poll_emails()
                await asyncio.sleep(settings.EMAIL_POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Error in email polling loop: {e}")
                await asyncio.sleep(settings.EMAIL_POLL_INTERVAL)

    def stop(self):
        """Stop the email polling loop."""
        logger.info("Stopping email poller")
        self.is_running = False

    async def poll_emails(self) -> Dict[str, Any]:
        """
        Poll for new emails and enqueue them for processing.

        Returns:
            Dict with processing results
        """
        self.poll_count += 1
        logger.info(f"Polling for emails (poll #{self.poll_count})")

        results = {
            "poll_number": self.poll_count,
            "queued": 0,
            "failed": 0,
            "emails": []
        }

        try:
            # Create fetcher
            fetcher = EmailFetcher(
                imap_server=settings.EMAIL_IMAP_SERVER,
                email_address=settings.EMAIL_ADDRESS,
                password=settings.EMAIL_PASSWORD,
                port=settings.EMAIL_PORT,
                use_ssl=settings.EMAIL_USE_SSL
            )

            # Fetch unread emails
            email_messages = fetcher.fetch_unread_emails(mark_as_read=True)

            if not email_messages:
                logger.info("No new emails found")
                return results

            logger.info(f"Enqueueing {len(email_messages)} email(s) for processing")

            # Enqueue each email for async processing
            for email_message in email_messages:
                try:
                    # Parse email to our schema
                    email_data = EmailParser.parse_to_ingest(email_message)

                    # Enqueue for background processing (with retry logic)
                    job = enqueue_email_processing(email_data)

                    results["queued"] += 1
                    results["emails"].append({
                        "subject": email_data.subject,
                        "job_id": job.id,
                        "status": "queued"
                    })

                    logger.info(f"Enqueued email for processing: {email_data.subject[:50]} (Job: {job.id})")

                except Exception as e:
                    results["failed"] += 1
                    results["emails"].append({
                        "subject": email_data.subject if 'email_data' in locals() else "Unknown",
                        "error": str(e)
                    })
                    logger.error(f"Failed to enqueue email: {e}")

        except Exception as e:
            logger.error(f"Error during email polling: {e}")
            results["error"] = str(e)

        logger.info(f"Poll complete: {results['queued']} queued, {results['failed']} failed")
        return results


# Global poller instance
email_poller = EmailPoller()
