"""
Attachment API endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.attachment import Attachment
from app.schemas.case import AttachmentResponse

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("/", response_model=List[AttachmentResponse])
def list_attachments(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = Query(None, description="Filter by category"),
    case_id: Optional[UUID] = Query(None, description="Filter by case ID"),
    db: Session = Depends(get_db)
):
    """
    List all attachments with optional filtering.

    Query parameters:
    - skip: Number of records to skip (for pagination)
    - limit: Maximum number of records to return
    - category: Filter by attachment category (medical_records, declaration, cover_letter, other)
    - case_id: Filter by case ID
    """
    query = db.query(Attachment)

    # Apply filters
    if category:
        query = query.filter(Attachment.category == category)

    if case_id:
        query = query.filter(Attachment.case_id == case_id)

    # Order by most recently created
    query = query.order_by(Attachment.created_at.desc())

    attachments = query.offset(skip).limit(limit).all()
    return attachments


@router.get("/by-category/{category}", response_model=List[AttachmentResponse])
def get_attachments_by_category(
    category: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all attachments of a specific category.

    Path parameter:
    - category: Attachment category (medical_records, declaration, cover_letter, other)
    """
    attachments = (
        db.query(Attachment)
        .filter(Attachment.category == category)
        .order_by(Attachment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return attachments


@router.get("/{attachment_id}", response_model=AttachmentResponse)
def get_attachment(attachment_id: UUID, db: Session = Depends(get_db)):
    """
    Get attachment details by ID.
    """
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    return attachment


@router.get("/case/{case_id}/attachments", response_model=List[AttachmentResponse])
def get_case_attachments(
    case_id: UUID,
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get all attachments for a specific case.

    Useful for retrieving all documents related to a case.

    Path parameter:
    - case_id: UUID of the case

    Query parameter:
    - category: Optional filter by attachment category
    """
    query = db.query(Attachment).filter(Attachment.case_id == case_id)

    if category:
        query = query.filter(Attachment.category == category)

    attachments = query.order_by(Attachment.created_at.desc()).all()

    return attachments
