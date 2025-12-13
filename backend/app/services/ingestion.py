"""
Email ingestion service - orchestrates the email processing pipeline.

This service:
1. Receives email data
2. Calls LLM extraction service
3. Matches or creates cases
4. Persists data to database
"""
from datetime import datetime, date, time as time_type
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.case import Case, CaseStatus
from app.models.email import Email, EmailProcessingStatus
from app.models.attachment import Attachment, AttachmentCategory
from app.schemas.email import EmailIngest
from app.schemas.extraction import CaseExtraction
from app.services.extraction import extract_case_from_email


def find_or_create_case(
    db: Session,
    extraction: CaseExtraction,
    existing_case_id: Optional[str] = None
) -> Case:
    """
    Find an existing case by case_number or create a new one.

    Args:
        db: Database session
        extraction: Extracted case data
        existing_case_id: Optional UUID of existing case to update

    Returns:
        Case: The found or created case
    """
    # Try to find existing case by case_number
    case = db.query(Case).filter(Case.case_number == extraction.case_number).first()

    if case:
        # Update existing case with new information (if more complete)
        # Only update fields that are None in existing case or have higher confidence
        if extraction.exam_date and not case.exam_date:
            try:
                case.exam_date = date.fromisoformat(extraction.exam_date)
            except (ValueError, TypeError):
                pass

        if extraction.exam_time and not case.exam_time:
            try:
                hour, minute = map(int, extraction.exam_time.split(':'))
                case.exam_time = time_type(hour, minute)
            except (ValueError, TypeError):
                pass

        if extraction.exam_location and not case.exam_location:
            case.exam_location = extraction.exam_location

        if extraction.referring_party and not case.referring_party:
            case.referring_party = extraction.referring_party

        if extraction.referring_email and not case.referring_email:
            case.referring_email = extraction.referring_email

        if extraction.report_due_date and not case.report_due_date:
            try:
                case.report_due_date = date.fromisoformat(extraction.report_due_date)
            except (ValueError, TypeError):
                pass

        # Update confidence if higher
        if extraction.confidence > (case.extraction_confidence or 0):
            case.extraction_confidence = extraction.confidence

        # Append to notes if there are extraction notes
        if extraction.extraction_notes:
            if case.notes:
                case.notes += f"\n\n[{datetime.utcnow().isoformat()}] {extraction.extraction_notes}"
            else:
                case.notes = extraction.extraction_notes

        case.updated_at = datetime.utcnow()

    else:
        # Create new case
        case = Case(
            case_number=extraction.case_number,
            patient_name=extraction.patient_name,
            exam_type=extraction.exam_type,
            status=CaseStatus.PENDING,
            extraction_confidence=extraction.confidence,
            notes=extraction.extraction_notes
        )

        # Parse optional date/time fields
        if extraction.exam_date:
            try:
                case.exam_date = date.fromisoformat(extraction.exam_date)
            except (ValueError, TypeError):
                pass

        if extraction.exam_time:
            try:
                hour, minute = map(int, extraction.exam_time.split(':'))
                case.exam_time = time_type(hour, minute)
            except (ValueError, TypeError):
                pass

        if extraction.exam_location:
            case.exam_location = extraction.exam_location

        if extraction.referring_party:
            case.referring_party = extraction.referring_party

        if extraction.referring_email:
            case.referring_email = extraction.referring_email

        if extraction.report_due_date:
            try:
                case.report_due_date = date.fromisoformat(extraction.report_due_date)
            except (ValueError, TypeError):
                pass

        db.add(case)
        db.flush()  # Get the case ID

    return case


def process_email(db: Session, email_data: EmailIngest) -> Email:
    """
    Process an incoming email through the full pipeline.

    Args:
        db: Database session
        email_data: Email data to process

    Returns:
        Email: The processed email record with linked case

    Raises:
        Exception: If processing fails critically
    """
    # Create email record
    email = Email(
        subject=email_data.subject,
        sender=email_data.sender,
        recipients=email_data.recipients,
        body=email_data.body,
        received_at=email_data.received_at,
        processing_status=EmailProcessingStatus.PROCESSING
    )

    try:
        # Extract case data using LLM
        extraction = extract_case_from_email(
            subject=email_data.subject,
            sender=email_data.sender,
            body=email_data.body,
            attachments=[att.model_dump() for att in email_data.attachments]
        )

        # Store raw extraction for debugging
        email.raw_extraction = extraction.model_dump()

        # Find or create case
        case = find_or_create_case(db, extraction)
        email.case_id = case.id

        # Process attachments
        for att_data, att_extraction in zip(email_data.attachments, extraction.attachments):
            attachment = Attachment(
                email_id=email.id,
                case_id=case.id,
                filename=att_data.filename,
                content_type=att_data.content_type,
                content_preview=att_data.text_content[:500] if att_data.text_content else None,
                category=AttachmentCategory(att_extraction.category),
                category_reason=att_extraction.category_reason
            )
            db.add(attachment)

        # Mark as processed
        email.processing_status = EmailProcessingStatus.PROCESSED
        email.processed_at = datetime.utcnow()

        db.add(email)
        db.commit()
        db.refresh(email)

        return email

    except Exception as e:
        # Mark as failed but keep the data
        email.processing_status = EmailProcessingStatus.FAILED
        email.error_message = str(e)
        email.processed_at = datetime.utcnow()

        db.add(email)
        db.commit()
        db.refresh(email)

        raise e


def batch_process_sample_emails(db: Session, sample_dir: str = "sample_emails") -> Dict[str, Any]:
    """
    Process all sample emails from the sample_emails directory.

    Args:
        db: Database session
        sample_dir: Directory containing sample email JSON files

    Returns:
        Dict with processing results summary
    """
    import os
    import json
    from pathlib import Path

    results = {
        "processed": 0,
        "failed": 0,
        "emails": []
    }

    # Get all JSON files from sample directory
    base_path = Path(__file__).parent.parent.parent / sample_dir
    if not base_path.exists():
        return {"error": f"Sample directory not found: {base_path}"}

    for filename in sorted(os.listdir(base_path)):
        if not filename.endswith('.json'):
            continue

        try:
            with open(base_path / filename, 'r') as f:
                email_json = json.load(f)

            # Convert to EmailIngest schema
            email_data = EmailIngest(
                subject=email_json['subject'],
                sender=email_json['sender'],
                recipients=email_json['recipients'],
                body=email_json['body'],
                attachments=[
                    {
                        "filename": att['filename'],
                        "content_type": att.get('content_type'),
                        "text_content": att.get('text_content')
                    }
                    for att in email_json.get('attachments', [])
                ],
                received_at=datetime.fromisoformat(email_json['received_at'].replace('Z', '+00:00'))
            )

            # Process email
            email = process_email(db, email_data)

            results["processed"] += 1
            results["emails"].append({
                "filename": filename,
                "email_id": str(email.id),
                "case_id": str(email.case_id) if email.case_id else None,
                "status": email.processing_status.value
            })

        except Exception as e:
            results["failed"] += 1
            results["emails"].append({
                "filename": filename,
                "error": str(e)
            })

    return results
