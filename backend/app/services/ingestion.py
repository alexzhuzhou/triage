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
from app.schemas.email import EmailIngest, AttachmentData
from app.schemas.extraction import CaseExtraction
from app.services.extraction import extract_case_from_email


def find_or_create_case(
    db: Session,
    extraction: CaseExtraction,
    existing_case_id: Optional[str] = None
) -> Case:
    """
    Find an existing case by case_number or create a new one.

    Update Strategy:
    - If new extraction has HIGHER confidence: Update all fields (Option 3)
    - If new extraction has LOWER confidence: Only fill empty fields, flag conflicts (Option 4)

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
        current_confidence = case.extraction_confidence or 0
        new_confidence = extraction.confidence
        conflicts = []  # Track conflicts for manual review

        # Option 3: High confidence extraction - update ALL fields
        if new_confidence > current_confidence:
            # Update exam_date
            if extraction.exam_date:
                try:
                    case.exam_date = date.fromisoformat(extraction.exam_date)
                except (ValueError, TypeError):
                    pass

            # Update exam_time
            if extraction.exam_time:
                try:
                    hour, minute = map(int, extraction.exam_time.split(':'))
                    case.exam_time = time_type(hour, minute)
                except (ValueError, TypeError):
                    pass

            # Update other fields
            if extraction.exam_location:
                case.exam_location = extraction.exam_location
            if extraction.referring_party:
                case.referring_party = extraction.referring_party
            if extraction.referring_email:
                case.referring_email = extraction.referring_email

            # Update report_due_date
            if extraction.report_due_date:
                try:
                    case.report_due_date = date.fromisoformat(extraction.report_due_date)
                except (ValueError, TypeError):
                    pass

            # Update confidence
            case.extraction_confidence = new_confidence

            # Add note about high-confidence update
            update_note = f"[{datetime.utcnow().isoformat()}] AUTO-UPDATED: Higher confidence extraction ({new_confidence:.2f} > {current_confidence:.2f})"
            if extraction.extraction_notes:
                update_note += f" - {extraction.extraction_notes}"

            if case.notes:
                case.notes += f"\n\n{update_note}"
            else:
                case.notes = update_note

        # Option 4: Lower/equal confidence - fill empty fields, flag conflicts
        else:
            # Check for conflicts and flag them
            if extraction.exam_date:
                try:
                    new_exam_date = date.fromisoformat(extraction.exam_date)
                    if case.exam_date and case.exam_date != new_exam_date:
                        conflicts.append(f"Exam Date: {case.exam_date} -> {new_exam_date}")
                    elif not case.exam_date:
                        case.exam_date = new_exam_date
                except (ValueError, TypeError):
                    pass

            if extraction.exam_time:
                try:
                    hour, minute = map(int, extraction.exam_time.split(':'))
                    new_exam_time = time_type(hour, minute)
                    if case.exam_time and case.exam_time != new_exam_time:
                        conflicts.append(f"Exam Time: {case.exam_time} -> {new_exam_time}")
                    elif not case.exam_time:
                        case.exam_time = new_exam_time
                except (ValueError, TypeError):
                    pass

            if extraction.exam_location:
                if case.exam_location and case.exam_location != extraction.exam_location:
                    conflicts.append(f"Location: {case.exam_location} -> {extraction.exam_location}")
                elif not case.exam_location:
                    case.exam_location = extraction.exam_location

            if extraction.referring_party:
                if case.referring_party and case.referring_party != extraction.referring_party:
                    conflicts.append(f"Referring Party: {case.referring_party} -> {extraction.referring_party}")
                elif not case.referring_party:
                    case.referring_party = extraction.referring_party

            if extraction.referring_email:
                if case.referring_email and case.referring_email != extraction.referring_email:
                    conflicts.append(f"Referring Email: {case.referring_email} -> {extraction.referring_email}")
                elif not case.referring_email:
                    case.referring_email = extraction.referring_email

            if extraction.report_due_date:
                try:
                    new_due_date = date.fromisoformat(extraction.report_due_date)
                    if case.report_due_date and case.report_due_date != new_due_date:
                        conflicts.append(f"Report Due: {case.report_due_date} -> {new_due_date}")
                    elif not case.report_due_date:
                        case.report_due_date = new_due_date
                except (ValueError, TypeError):
                    pass

            # If conflicts found, flag for manual review
            if conflicts:
                conflict_note = f"[{datetime.utcnow().isoformat()}] ⚠️ MANUAL REVIEW NEEDED (Low confidence: {new_confidence:.2f})\nConflicts detected:\n" + "\n".join(f"  - {c}" for c in conflicts)

                if case.notes:
                    case.notes += f"\n\n{conflict_note}"
                else:
                    case.notes = conflict_note

            # Append extraction notes if any
            if extraction.extraction_notes and not conflicts:
                if case.notes:
                    case.notes += f"\n\n[{datetime.utcnow().isoformat()}] {extraction.extraction_notes}"
                else:
                    case.notes = extraction.extraction_notes

        case.updated_at = datetime.utcnow()

        # Check for missing critical information
        _flag_missing_critical_fields(case)

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

        # Check for missing critical information in new case
        _flag_missing_critical_fields(case)

    return case


def _flag_missing_critical_fields(case: Case) -> None:
    """
    Check for missing critical fields and add a follow-up flag to notes.

    Critical fields:
    - exam_date: When the exam should occur
    - exam_location: Where the exam will take place
    - exam_time: What time the exam is scheduled (less critical)
    - report_due_date: Deadline for report submission

    Args:
        case: The case to check
    """
    missing_fields = []

    # Check critical fields
    if not case.exam_date:
        missing_fields.append("Exam Date")

    if not case.exam_location:
        missing_fields.append("Exam Location")

    if not case.report_due_date:
        missing_fields.append("Report Due Date")

    # Check semi-critical fields
    if not case.exam_time:
        missing_fields.append("Exam Time")

    # If any critical info is missing, flag for follow-up
    if missing_fields:
        flag_note = f"[{datetime.utcnow().isoformat()}] 🔔 FOLLOW-UP REQUIRED\nMissing critical information:\n" + "\n".join(f"  - {field}" for field in missing_fields)
        flag_note += "\n\nAction needed: Contact referring party to obtain missing details."

        if case.notes:
            # Check if we already have a follow-up flag (avoid duplicates)
            if "FOLLOW-UP REQUIRED" not in case.notes:
                case.notes += f"\n\n{flag_note}"
        else:
            case.notes = flag_note


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
        received_at=email_data.received_at or datetime.utcnow(),
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

        # Add email to session and flush to get the ID
        db.add(email)
        db.flush()  # This assigns the ID to email.id

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
        db.commit()
        db.refresh(email)

        return email

    except Exception as e:
        # Rollback any partial transaction
        db.rollback()

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
