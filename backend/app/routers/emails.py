"""
Email API endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.email import Email
from app.schemas.email import EmailIngest, EmailResponse, AttachmentData
from app.services.queue import enqueue_email_processing

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("/ingest", status_code=202)
def ingest_email(email_data: EmailIngest, db: Session = Depends(get_db)):
    """
    Ingest a new email for processing.

    This endpoint enqueues the email for background processing with automatic
    retry logic for transient failures (OpenAI API timeouts, rate limits, etc.).

    Returns immediately with job ID for tracking.
    """
    try:
        job = enqueue_email_processing(email_data)
        return {
            "job_id": job.id,
            "status": "queued",
            "subject": email_data.subject,
            "message": "Email queued for processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue email: {str(e)}")


@router.post("/simulate-batch")
def simulate_batch_ingestion(db: Session = Depends(get_db)):
    """
    Process all sample emails from the sample_emails directory.

    Loads sample emails and enqueues them for background processing with retry logic.
    This is useful for testing and demonstration purposes.
    """
    import os
    import json
    from pathlib import Path
    from datetime import datetime

    try:
        results = {
            "queued": 0,
            "failed": 0,
            "emails": []
        }

        # Get all JSON files from sample directory
        base_path = Path(__file__).parent.parent.parent / "sample_emails"
        if not base_path.exists():
            raise HTTPException(status_code=404, detail=f"Sample directory not found: {base_path}")

        for filename in sorted(os.listdir(base_path)):
            if not filename.endswith('.json'):
                continue

            try:
                with open(base_path / filename, 'r', encoding='utf-8') as f:
                    email_json = json.load(f)

                # Convert to EmailIngest schema
                email_data = EmailIngest(
                    subject=email_json['subject'],
                    sender=email_json['sender'],
                    recipients=email_json['recipients'],
                    body=email_json['body'],
                    attachments=[
                        AttachmentData(
                            filename=att['filename'],
                            content_type=att.get('content_type'),
                            text_content=att.get('text_content')
                        )
                        for att in email_json.get('attachments', [])
                    ],
                    received_at=datetime.fromisoformat(email_json['received_at'].replace('Z', '+00:00')) if email_json.get('received_at') else None
                )

                # Enqueue for background processing
                job = enqueue_email_processing(email_data)

                results["queued"] += 1
                results["emails"].append({
                    "filename": filename,
                    "job_id": job.id,
                    "subject": email_data.subject,
                    "status": "queued"
                })

            except Exception as e:
                results["failed"] += 1
                results["emails"].append({
                    "filename": filename,
                    "error": str(e)
                })

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.get("/{email_id}", response_model=EmailResponse)
def get_email(email_id: UUID, db: Session = Depends(get_db)):
    """
    Get email details by ID, including extraction results.
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    return email


@router.get("/", response_model=List[EmailResponse])
def list_emails(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    List all emails with optional filtering.

    Query parameters:
    - skip: Number of records to skip (for pagination)
    - limit: Maximum number of records to return
    - status: Filter by processing status (pending, processing, processed, failed)
    """
    query = db.query(Email)

    if status:
        query = query.filter(Email.processing_status == status)

    emails = query.offset(skip).limit(limit).all()
    return emails


@router.post("/{email_id}/retry")
def retry_failed_email(email_id: UUID, db: Session = Depends(get_db)):
    """
    Retry processing a failed email.

    This endpoint allows you to manually retry emails that failed after all
    automatic retry attempts were exhausted.

    Returns:
        Job information for tracking the retry
    """
    from app.schemas.email import EmailIngest, AttachmentData

    # Find the failed email
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    if email.processing_status.value != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Email is not in failed status (current status: {email.processing_status.value})"
        )

    try:
        # Convert email back to EmailIngest format using saved raw data
        if email.raw_email_data:
            # Perfect replay: use original email data with attachments
            email_data = EmailIngest(**email.raw_email_data)
        else:
            # Fallback: reconstruct from database (attachments will be lost)
            email_data = EmailIngest(
                subject=email.subject,
                sender=email.sender,
                recipients=email.recipients,
                body=email.body,
                attachments=[],
                received_at=email.received_at
            )

        # Re-enqueue for processing
        job = enqueue_email_processing(email_data)

        return {
            "email_id": str(email.id),
            "job_id": job.id,
            "status": "queued",
            "message": "Email re-queued for processing",
            "previous_error": email.error_message
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry email: {str(e)}")


@router.post("/retry-all-failed")
def retry_all_failed_emails(db: Session = Depends(get_db)):
    """
    Retry all failed emails.

    This endpoint re-queues all emails with 'failed' status for processing.

    Returns:
        Summary of retry operation
    """
    from app.schemas.email import EmailIngest

    try:
        # Get all failed emails
        failed_emails = db.query(Email).filter(
            Email.processing_status == "failed"
        ).all()

        if not failed_emails:
            return {
                "message": "No failed emails found",
                "retried": 0,
                "emails": []
            }

        results = {
            "retried": 0,
            "failed_to_retry": 0,
            "emails": []
        }

        for email in failed_emails:
            try:
                # Convert back to EmailIngest using saved raw data
                if email.raw_email_data:
                    # Perfect replay: use original email data with attachments
                    email_data = EmailIngest(**email.raw_email_data)
                else:
                    # Fallback: reconstruct from database (attachments will be lost)
                    email_data = EmailIngest(
                        subject=email.subject,
                        sender=email.sender,
                        recipients=email.recipients,
                        body=email.body,
                        attachments=[],
                        received_at=email.received_at
                    )

                # Re-enqueue
                job = enqueue_email_processing(email_data)

                results["retried"] += 1
                results["emails"].append({
                    "email_id": str(email.id),
                    "job_id": job.id,
                    "subject": email.subject,
                    "status": "queued"
                })

            except Exception as e:
                results["failed_to_retry"] += 1
                results["emails"].append({
                    "email_id": str(email.id),
                    "subject": email.subject,
                    "error": str(e)
                })

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry emails: {str(e)}")
