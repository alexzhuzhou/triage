"""
Tests for API endpoints.
"""
import pytest
from datetime import datetime

from app.models.case import Case, CaseStatus
from app.models.email import Email, EmailProcessingStatus


def test_root_endpoint(client):
    """Test root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "endpoints" in data


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_cases_empty(client):
    """Test listing cases when database is empty."""
    response = client.get("/cases/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_cases_with_data(client, db):
    """Test listing cases with data."""
    # Create test cases
    case1 = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic",
        status=CaseStatus.PENDING,
        extraction_confidence=0.9
    )
    case2 = Case(
        case_number="TEST-002",
        patient_name="Jane Smith",
        exam_type="Neurology",
        status=CaseStatus.CONFIRMED,
        extraction_confidence=0.85
    )
    db.add_all([case1, case2])
    db.commit()

    response = client.get("/cases/")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 2


def test_get_case_by_id(client, db):
    """Test getting a specific case by ID."""
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic",
        extraction_confidence=0.95
    )
    db.add(case)
    db.commit()

    response = client.get(f"/cases/{case.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["case_number"] == "TEST-001"
    assert data["patient_name"] == "John Doe"


def test_get_case_not_found(client):
    """Test getting a non-existent case."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/cases/{fake_uuid}")
    assert response.status_code == 404


def test_update_case(client, db):
    """Test updating case fields."""
    case = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic"
    )
    db.add(case)
    db.commit()

    # Update case
    update_data = {
        "status": "confirmed",
        "notes": "Confirmed with patient"
    }
    response = client.patch(f"/cases/{case.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"
    assert data["notes"] == "Confirmed with patient"


def test_filter_cases_by_confidence(client, db):
    """Test filtering cases by minimum confidence."""
    case1 = Case(
        case_number="TEST-001",
        patient_name="John Doe",
        exam_type="Orthopedic",
        extraction_confidence=0.95
    )
    case2 = Case(
        case_number="TEST-002",
        patient_name="Jane Smith",
        exam_type="Neurology",
        extraction_confidence=0.60
    )
    db.add_all([case1, case2])
    db.commit()

    # Filter for high confidence only
    response = client.get("/cases/?min_confidence=0.8")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 1
    assert cases[0]["case_number"] == "TEST-001"


def test_list_emails(client, db):
    """Test listing emails."""
    # Create test case and email
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

    response = client.get("/emails/")
    assert response.status_code == 200
    emails = response.json()
    assert len(emails) == 1
    assert emails[0]["subject"] == "Test Email"
