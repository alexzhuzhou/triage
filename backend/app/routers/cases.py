"""
Case API endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.case import Case
from app.schemas.case import CaseResponse, CaseUpdate

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/", response_model=List[CaseResponse])
def list_cases(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None, description="Filter by status (pending, confirmed, completed)"),
    exam_type: Optional[str] = Query(None, description="Filter by exam type"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold (0.0-1.0)"),
    db: Session = Depends(get_db)
):
    """
    List all cases with optional filtering.

    Query parameters:
    - skip: Number of records to skip (for pagination)
    - limit: Maximum number of records to return
    - status: Filter by case status
    - exam_type: Filter by examination type
    - min_confidence: Only return cases with confidence >= this value
    """
    query = db.query(Case)

    # Apply filters
    if status:
        query = query.filter(Case.status == status)

    if exam_type:
        query = query.filter(Case.exam_type.ilike(f"%{exam_type}%"))

    if min_confidence is not None:
        query = query.filter(Case.extraction_confidence >= min_confidence)

    # Order by most recently updated
    query = query.order_by(Case.updated_at.desc())

    cases = query.offset(skip).limit(limit).all()
    return cases


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: UUID, db: Session = Depends(get_db)):
    """
    Get full case details by ID, including emails and attachments.
    """
    case = db.query(Case).options(
        joinedload(Case.emails),
        joinedload(Case.attachments)
    ).filter(Case.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(case_id: UUID, case_update: CaseUpdate, db: Session = Depends(get_db)):
    """
    Update case fields.

    This endpoint allows manual correction or updating of case information.
    All fields are optional - only provided fields will be updated.
    """
    case = db.query(Case).filter(Case.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Update only provided fields
    update_data = case_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)

    return case


@router.get("/by-number/{case_number}", response_model=CaseResponse)
def get_case_by_number(case_number: str, db: Session = Depends(get_db)):
    """
    Get case by case number (e.g., NF-39281).
    """
    case = db.query(Case).options(
        joinedload(Case.emails),
        joinedload(Case.attachments)
    ).filter(Case.case_number == case_number).first()

    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_number} not found")

    return case


@router.delete("/{case_id}")
def delete_case(case_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a case and all associated emails and attachments.

    WARNING: This is a permanent operation and cannot be undone.
    All related data (emails, attachments) will also be deleted due to CASCADE.
    """
    case = db.query(Case).filter(Case.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Delete the case (CASCADE will handle related emails and attachments)
    db.delete(case)
    db.commit()

    return {
        "message": "Case deleted successfully",
        "case_id": str(case_id),
        "case_number": case.case_number
    }
