"""Quick test script to verify GCS is working."""
import os

# Set GCS_ENABLED if not already set
if not os.environ.get('GCS_ENABLED'):
    os.environ['GCS_ENABLED'] = 'true'

# Load settings from environment (.env file)
from app.services.gcs_storage import get_gcs_service

print("Testing GCS service...")
gcs = get_gcs_service()

if gcs.client:
    print("✓ GCS client initialized successfully")
    print(f"✓ Project ID: {gcs.client.project}")
    print(f"✓ Bucket name: {gcs.bucket_name}")

    # Test upload
    test_data = b"Hello from test"
    result = gcs.upload_attachment(
        file_data=test_data,
        case_number="TEST-001",
        filename="test.txt",
        content_type="text/plain"
    )

    if result:
        print(f"✓ Upload successful: {result['file_path']}")
    else:
        print("✗ Upload failed")
else:
    print("✗ GCS client failed to initialize")
