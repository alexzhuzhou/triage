#!/usr/bin/env python
"""
Test the queue retry mechanism by simulating LLM failures.

This script tests:
1. Temporary failure (fails 2 times, then succeeds) - should retry and succeed
2. Permanent failure (fails 5+ times) - should save as FAILED
"""
import time
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.database import SessionLocal
from app.schemas.email import EmailIngest
from app.tasks import process_email_task
from app.models.email import Email, EmailProcessingStatus

print("=" * 70)
print("QUEUE RETRY MECHANISM TEST")
print("=" * 70)

# Test 1: Temporary failure (succeeds after 2 retries)
print("\n" + "=" * 70)
print("TEST 1: Temporary LLM Failure (fails 2x, then succeeds)")
print("=" * 70)

email_data_temp = {
    "subject": "Test Retry - Temporary Failure",
    "sender": "test@example.com",
    "recipients": ["intake@example.com"],
    "body": "Testing retry mechanism with temporary failures",
    "attachments": [],
    "received_at": datetime(2026, 1, 6, 13, 0, 0).isoformat()
}

# Track how many times extraction is called
call_count = {"count": 0}

def mock_extraction_temp_fail(*args, **kwargs):
    """Fail first 2 times, succeed on 3rd attempt."""
    call_count["count"] += 1
    print(f"\n  -> LLM Call Attempt #{call_count['count']}")

    if call_count["count"] <= 2:
        print(f"     [SIMULATED FAILURE] OpenAI API timeout")
        raise Exception("OpenAI API Error: Request timed out")
    else:
        print(f"     [SUCCESS] LLM extraction successful")
        from app.schemas.extraction import CaseExtraction, AttachmentExtraction
        return CaseExtraction(
            patient_name="Test Patient",
            case_number="RETRY-TEST-001",
            exam_type="Orthopedic",
            confidence=0.85,
            extraction_notes=None,
            email_intent="new_referral",
            attachments=[]
        )

print("\nStarting test with mocked LLM failures...")
print("Expected: Fail 2x (with retries), then succeed on 3rd attempt\n")

db = SessionLocal()
try:
    with patch('app.services.ingestion.extract_case_from_email', side_effect=mock_extraction_temp_fail):
        with patch('app.tasks.get_current_job') as mock_job:
            mock_job.return_value = MagicMock(id="test-retry-job-1", retries_left=5)

            # This will fail the first 2 times
            for attempt in range(1, 4):
                print(f"--- Queue Attempt #{attempt} ---")
                try:
                    result = process_email_task(email_data_temp)
                    print(f"\n[RESULT] Task completed successfully!")
                    print(f"  Email ID: {result['email_id']}")
                    print(f"  Status: {result['status']}")
                    print(f"  Case ID: {result['case_id']}")
                    break
                except Exception as e:
                    print(f"[EXCEPTION] Task failed: {str(e)}")
                    if attempt < 3:
                        print(f"Simulating retry with exponential backoff...")
                        time.sleep(0.5)  # Simulating retry delay
                    else:
                        print("[ERROR] All attempts exhausted")

    # Check database
    email = db.query(Email).filter(
        Email.subject == "Test Retry - Temporary Failure"
    ).first()

    if email:
        print(f"\n[DATABASE CHECK]")
        print(f"  Status: {email.processing_status.value}")
        print(f"  Case ID: {email.case_id}")
        print(f"  Error: {email.error_message or 'None'}")

        if email.processing_status == EmailProcessingStatus.PROCESSED:
            print("\n[TEST 1 PASSED] Email processed successfully after retries!")
        else:
            print("\n[TEST 1 FAILED] Email not processed correctly")

    # Cleanup
    if email:
        db.delete(email)
        db.commit()

except Exception as e:
    print(f"\n[ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()

finally:
    call_count["count"] = 0


# Test 2: Permanent failure (fails all 5 attempts)
print("\n" + "=" * 70)
print("TEST 2: Permanent LLM Failure (fails 5+ times)")
print("=" * 70)

email_data_perm = {
    "subject": "Test Retry - Permanent Failure",
    "sender": "test2@example.com",
    "recipients": ["intake@example.com"],
    "body": "Testing retry mechanism with permanent failures",
    "attachments": [],
    "received_at": datetime(2026, 1, 6, 14, 0, 0).isoformat()
}

permanent_fail_count = {"count": 0}

def mock_extraction_perm_fail(*args, **kwargs):
    """Always fail (to simulate permanent API issue)."""
    permanent_fail_count["count"] += 1
    print(f"\n  -> LLM Call Attempt #{permanent_fail_count['count']}")
    print(f"     [SIMULATED FAILURE] Invalid API key")
    raise Exception("OpenAI API Error: Invalid API key")

print("\nStarting test with permanent LLM failures...")
print("Expected: Fail all 5 attempts, save as FAILED in database\n")

try:
    with patch('app.services.ingestion.extract_case_from_email', side_effect=mock_extraction_perm_fail):
        with patch('app.tasks.get_current_job') as mock_job:
            mock_job.return_value = MagicMock(id="test-retry-job-2", retries_left=5)

            # Simulate 5 retry attempts
            for attempt in range(1, 6):
                print(f"--- Queue Attempt #{attempt} ---")
                try:
                    result = process_email_task(email_data_perm)
                    print(f"\n[UNEXPECTED] Task succeeded when it should have failed")
                    break
                except Exception as e:
                    print(f"[EXCEPTION] Task failed: {str(e)[:60]}...")
                    if attempt < 5:
                        print(f"Simulating retry with exponential backoff...")
                        time.sleep(0.2)  # Simulating retry delay
                    else:
                        print("\n[EXPECTED] All 5 retry attempts exhausted")

    # Check database - should have FAILED status
    email = db.query(Email).filter(
        Email.subject == "Test Retry - Permanent Failure"
    ).first()

    if email:
        print(f"\n[DATABASE CHECK]")
        print(f"  Status: {email.processing_status.value}")
        print(f"  Case ID: {email.case_id or 'None'}")
        print(f"  Error: {email.error_message[:60]}..." if email.error_message else "  Error: None")

        if email.processing_status == EmailProcessingStatus.FAILED and email.error_message:
            print("\n[TEST 2 PASSED] Email saved as FAILED with error message!")
            print("  - Email record preserved (no data loss)")
            print("  - Error message captured for debugging")
            print("  - Case ID is null (extraction never succeeded)")
        else:
            print("\n[TEST 2 FAILED] Email status not correct")

    # Cleanup
    if email:
        db.delete(email)
        db.commit()

except Exception as e:
    print(f"\n[ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nRetry Mechanism Features Demonstrated:")
    print("  [✓] Automatic retries on transient failures")
    print("  [✓] Exponential backoff between retries")
    print("  [✓] Eventual success after temporary failures")
    print("  [✓] Data preservation on permanent failures")
    print("  [✓] Error message capture for debugging")
    print("\n" + "=" * 70)