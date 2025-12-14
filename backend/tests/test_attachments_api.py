"""
Tests for Attachment API endpoints.
"""
import pytest
from datetime import datetime

from app.models.case import Case, CaseStatus
from app.models.email import Email, EmailProcessingStatus
from app.models.attachment import Attachment, AttachmentCategory


def test_list_attachments_empty(client):
    """Test listing attachments when database is empty."""
    response = client.get("/attachments/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_attachments_with_data(client, db):
    """Test listing attachments with data."""
    # Create test case
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic"
    )
    db.add(case)
    db.commit()

    # Create test email
    email = Email(
        case_id=case.id,
        subject="Test Email",
        sender="test@example.com",
        recipients=["intake@ime.com"],
        body="Test body",
        received_at=datetime.utcnow(),
        processing_status=EmailProcessingStatus.PROCESSED
    )
    db.add(email)
    db.commit()

    # Create test attachments
    att1 = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="medical_records.pdf",
        content_type="application/pdf",
        category=AttachmentCategory.MEDICAL_RECORDS
    )
    att2 = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="declaration.pdf",
        content_type="application/pdf",
        category=AttachmentCategory.DECLARATION
    )
    db.add_all([att1, att2])
    db.commit()

    response = client.get("/attachments/")
    assert response.status_code == 200
    attachments = response.json()
    assert len(attachments) == 2


def test_filter_attachments_by_category(client, db):
    """Test filtering attachments by category."""
    # Create test data
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic"
    )
    db.add(case)
    db.commit()

    email = Email(
        case_id=case.id,
        subject="Test Email",
        sender="test@example.com",
        recipients=["intake@ime.com"],
        body="Test body",
        received_at=datetime.utcnow(),
        processing_status=EmailProcessingStatus.PROCESSED
    )
    db.add(email)
    db.commit()

    att1 = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="medical_records.pdf",
        category=AttachmentCategory.MEDICAL_RECORDS
    )
    att2 = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="declaration.pdf",
        category=AttachmentCategory.DECLARATION
    )
    db.add_all([att1, att2])
    db.commit()

    # Filter by medical_records
    response = client.get("/attachments/?category=medical_records")
    assert response.status_code == 200
    attachments = response.json()
    assert len(attachments) == 1
    assert attachments[0]["category"] == "medical_records"


def test_get_attachments_by_category(client, db):
    """Test get attachments by category endpoint."""
    # Create test data
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic"
    )
    db.add(case)
    db.commit()

    email = Email(
        case_id=case.id,
        subject="Test Email",
        sender="test@example.com",
        recipients=["intake@ime.com"],
        body="Test body",
        received_at=datetime.utcnow(),
        processing_status=EmailProcessingStatus.PROCESSED
    )
    db.add(email)
    db.commit()

    att = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="medical_records.pdf",
        category=AttachmentCategory.MEDICAL_RECORDS
    )
    db.add(att)
    db.commit()

    response = client.get("/attachments/by-category/medical_records")
    assert response.status_code == 200
    attachments = response.json()
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "medical_records.pdf"


def test_get_attachment_by_id(client, db):
    """Test getting a specific attachment by ID."""
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic"
    )
    db.add(case)
    db.commit()

    email = Email(
        case_id=case.id,
        subject="Test Email",
        sender="test@example.com",
        recipients=["intake@ime.com"],
        body="Test body",
        received_at=datetime.utcnow(),
        processing_status=EmailProcessingStatus.PROCESSED
    )
    db.add(email)
    db.commit()

    att = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="medical_records.pdf",
        category=AttachmentCategory.MEDICAL_RECORDS
    )
    db.add(att)
    db.commit()

    response = client.get(f"/attachments/{att.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "medical_records.pdf"
    assert data["category"] == "medical_records"


def test_get_attachment_not_found(client):
    """Test getting a non-existent attachment."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/attachments/{fake_uuid}")
    assert response.status_code == 404


def test_get_case_attachments(client, db):
    """Test getting all attachments for a specific case."""
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic"
    )
    db.add(case)
    db.commit()

    email = Email(
        case_id=case.id,
        subject="Test Email",
        sender="test@example.com",
        recipients=["intake@ime.com"],
        body="Test body",
        received_at=datetime.utcnow(),
        processing_status=EmailProcessingStatus.PROCESSED
    )
    db.add(email)
    db.commit()

    att1 = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="medical_records.pdf",
        category=AttachmentCategory.MEDICAL_RECORDS
    )
    att2 = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="declaration.pdf",
        category=AttachmentCategory.DECLARATION
    )
    db.add_all([att1, att2])
    db.commit()

    response = client.get(f"/attachments/case/{case.id}/attachments")
    assert response.status_code == 200
    attachments = response.json()
    assert len(attachments) == 2


def test_attachment_response_includes_storage_fields(client, db):
    """Test that attachment response includes new storage fields."""
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic"
    )
    db.add(case)
    db.commit()

    email = Email(
        case_id=case.id,
        subject="Test Email",
        sender="test@example.com",
        recipients=["intake@ime.com"],
        body="Test body",
        received_at=datetime.utcnow(),
        processing_status=EmailProcessingStatus.PROCESSED
    )
    db.add(email)
    db.commit()

    att = Attachment(
        email_id=email.id,
        case_id=case.id,
        filename="medical_records.pdf",
        category=AttachmentCategory.MEDICAL_RECORDS,
        file_path="s3://bucket/test.pdf",
        file_size=1024,
        storage_provider="s3"
    )
    db.add(att)
    db.commit()

    response = client.get(f"/attachments/{att.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["file_path"] == "s3://bucket/test.pdf"
    assert data["file_size"] == 1024
    assert data["storage_provider"] == "s3"
