"""
Email API endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.email import Email
from app.schemas.email import EmailIngest, EmailResponse
from app.services.ingestion import process_email, batch_process_sample_emails

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("/ingest", response_model=EmailResponse, status_code=201)
def ingest_email(email_data: EmailIngest, db: Session = Depends(get_db)):
    """
    Ingest a new email for processing.

    This endpoint:
    1. Receives email data
    2. Extracts case information using LLM
    3. Creates or updates case records
    4. Stores email and attachments
    """
    try:
        email = process_email(db, email_data)
        return email
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process email: {str(e)}")


@router.post("/simulate-batch")
def simulate_batch_ingestion(db: Session = Depends(get_db)):
    """
    Process all sample emails from the sample_emails directory.

    This is useful for testing and demonstration purposes.
    """
    try:
        results = batch_process_sample_emails(db)
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
