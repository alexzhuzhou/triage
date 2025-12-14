"""
Email polling API endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.config import settings
from app.services.email_fetcher import EmailFetcher
from app.services.email_parser import EmailParser
from app.services.ingestion import process_email

router = APIRouter(prefix="/email-polling", tags=["email-polling"])


@router.post("/manual-poll", response_model=Dict[str, Any])
def manual_poll_emails(db: Session = Depends(get_db)):
    """
    Manually trigger email polling.

    Useful for testing or on-demand email fetching.
    Connects to email server, fetches unread emails, and processes them.

    Returns:
        Processing results summary
    """
    if not settings.EMAIL_ENABLED:
        return {
            "error": "Email polling is disabled. Set EMAIL_ENABLED=true in .env"
        }

    if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
        return {
            "error": "Email credentials not configured. Check EMAIL_ADDRESS and EMAIL_PASSWORD in .env"
        }

    results = {
        "processed": 0,
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
            return {
                "message": "No new emails found",
                "processed": 0,
                "failed": 0,
                "emails": []
            }

        # Process each email
        for email_message in email_messages:
            try:
                # Parse email to our schema
                email_data = EmailParser.parse_to_ingest(email_message)

                # Process through ingestion pipeline
                processed_email = process_email(db, email_data)

                results["processed"] += 1
                results["emails"].append({
                    "subject": email_data.subject,
                    "email_id": str(processed_email.id),
                    "case_id": str(processed_email.case_id) if processed_email.case_id else None,
                    "status": processed_email.processing_status.value
                })

            except Exception as e:
                results["failed"] += 1
                results["emails"].append({
                    "subject": email_data.subject if 'email_data' in locals() else "Unknown",
                    "error": str(e)
                })

    except Exception as e:
        return {
            "error": f"Failed to fetch emails: {str(e)}",
            "processed": results["processed"],
            "failed": results["failed"]
        }

    return results


@router.get("/status")
def get_polling_status():
    """
    Get email polling configuration status.

    Returns:
        Current email polling configuration
    """
    return {
        "enabled": settings.EMAIL_ENABLED,
        "configured": bool(settings.EMAIL_ADDRESS and settings.EMAIL_PASSWORD),
        "imap_server": settings.EMAIL_IMAP_SERVER,
        "email_address": settings.EMAIL_ADDRESS if settings.EMAIL_ADDRESS else "Not configured",
        "poll_interval": settings.EMAIL_POLL_INTERVAL,
        "port": settings.EMAIL_PORT,
        "use_ssl": settings.EMAIL_USE_SSL
    }
