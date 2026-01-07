#!/usr/bin/env python
"""
REAL queue retry test - requires full stack running:
1. PostgreSQL (docker compose up -d postgres)
2. Redis (docker compose up -d redis)
3. Backend API (uvicorn app.main:app --reload --port 8000)
4. Worker (python -m app.worker)

This test actually uses the queue system.
"""
import requests
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_queue_with_real_worker():
    """Test that requires worker to be running."""

    print("=" * 70)
    print("REAL QUEUE INTEGRATION TEST")
    print("=" * 70)
    print("\nPrerequisites:")
    print("  1. PostgreSQL running: docker compose up -d postgres")
    print("  2. Redis running: docker compose up -d redis")
    print("  3. Backend API running: uvicorn app.main:app --reload --port 8000")
    print("  4. Worker running: python -m app.worker")
    print("=" * 70)

    # Check if backend is running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code != 200:
            print("\n[ERROR] Backend API is not running!")
            print("Start it with: uvicorn app.main:app --reload --port 8000")
            return
    except requests.exceptions.RequestException:
        print("\n[ERROR] Cannot connect to backend API!")
        print("Start it with: uvicorn app.main:app --reload --port 8000")
        return

    # Check if Redis/queue is working
    try:
        response = requests.get(f"{API_BASE}/queue/health", timeout=2)
        data = response.json()
        if not data.get("redis_connected"):
            print("\n[ERROR] Redis is not connected!")
            print("Start it with: docker compose up -d redis")
            return

        if data.get("workers_available", 0) == 0:
            print("\n[WARNING] No workers detected!")
            print("The test will enqueue the job, but it won't process without a worker.")
            print("Start worker with: python -m app.worker")
            print("\nContinuing anyway to show enqueuing...")
    except requests.exceptions.RequestException:
        print("\n[ERROR] Cannot check queue health")
        return

    print("\n[OK] All prerequisites met!\n")

    # Prepare test email
    email_data = {
        "subject": "Queue Integration Test",
        "sender": "queuetest@example.com",
        "recipients": ["intake@example.com"],
        "body": "This email tests the real queue system with worker retries",
        "attachments": [],
        "received_at": datetime.now().isoformat()
    }

    print("=" * 70)
    print("STEP 1: Enqueue Email via API")
    print("=" * 70)

    # Submit email to be processed
    response = requests.post(f"{API_BASE}/emails/ingest", json=email_data)

    if response.status_code == 200:
        result = response.json()
        print(f"\n[SUCCESS] Email enqueued!")

        if "job_id" in result:
            job_id = result["job_id"]
            print(f"  Job ID: {job_id}")
            print(f"  Status: {result.get('status', 'queued')}")

            print("\n" + "=" * 70)
            print("STEP 2: Monitor Job Processing (watching queue)")
            print("=" * 70)

            # Monitor the job for up to 30 seconds
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)

                # Check job status
                try:
                    job_response = requests.get(f"{API_BASE}/queue/jobs/{job_id}")
                    if job_response.status_code == 200:
                        job_data = job_response.json()
                        status = job_data.get("status", "unknown")

                        print(f"  [{i+1}s] Job status: {status}")

                        if status == "finished":
                            print("\n[SUCCESS] Job completed!")
                            print(f"  Result: {job_data.get('result', {})}")
                            break
                        elif status == "failed":
                            print("\n[FAILED] Job failed after retries")
                            print(f"  Error: {job_data.get('error', 'Unknown error')}")
                            break
                        elif status == "started":
                            print(f"         Worker is processing...")
                        elif status == "queued":
                            print(f"         Waiting for worker...")
                    else:
                        print(f"  [{i+1}s] Cannot fetch job status (might be cleaned up)")

                except requests.exceptions.RequestException as e:
                    print(f"  [{i+1}s] Error checking status: {e}")

            # Check queue stats
            print("\n" + "=" * 70)
            print("STEP 3: Final Queue Stats")
            print("=" * 70)

            queue_response = requests.get(f"{API_BASE}/queue/status")
            if queue_response.status_code == 200:
                stats = queue_response.json()
                default_queue = stats.get("queues", {}).get("default", {})

                print(f"\nDefault Queue:")
                print(f"  Queued: {default_queue.get('queued', 0)}")
                print(f"  Started: {default_queue.get('started', 0)}")
                print(f"  Finished: {default_queue.get('finished', 0)}")
                print(f"  Failed: {default_queue.get('failed', 0)}")
                print(f"  Workers: {default_queue.get('workers', 0)}")

            # Check if email was created in database
            print("\n" + "=" * 70)
            print("STEP 4: Database Check")
            print("=" * 70)

            # Wait a bit for processing to complete
            time.sleep(2)

            cases_response = requests.get(f"{API_BASE}/cases/")
            if cases_response.status_code == 200:
                cases = cases_response.json()
                test_case = None
                for case in cases:
                    if case.get("referring_email") == "queuetest@example.com":
                        test_case = case
                        break

                if test_case:
                    print(f"\n[FOUND] Case created in database!")
                    print(f"  Case Number: {test_case.get('case_number')}")
                    print(f"  Patient: {test_case.get('patient_name')}")
                    print(f"  Confidence: {test_case.get('extraction_confidence')}")
                else:
                    print(f"\n[NOT FOUND] Case not yet in database")
                    print(f"  (Check if worker is running and processing jobs)")
        else:
            print(f"\n[INFO] Response: {result}")
            print("  (Might have used sync fallback if Redis was down)")
    else:
        print(f"\n[ERROR] Failed to enqueue email")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("\nWhat this test demonstrates:")
    print("  - Email enqueued via REST API")
    print("  - Job created in Redis queue")
    print("  - Worker picks up job from queue")
    print("  - Worker processes with automatic retries")
    print("  - Results saved to database")
    print("\nTo see retry behavior:")
    print("  1. Temporarily break your OpenAI API key in .env")
    print("  2. Run this test")
    print("  3. Watch worker logs show 5 retry attempts")
    print("  4. Check queue stats show 'failed: 1'")
    print("=" * 70)

if __name__ == "__main__":
    test_queue_with_real_worker()