# Google Cloud Storage Setup Guide

This guide explains how to set up Google Cloud Storage (GCS) for attachment storage in the Triage application.

## Overview

Attachments (PDFs, text files, etc.) are uploaded to Google Cloud Storage during email processing. The system:
1. **Stores original files** in GCS (organized by case number)
2. **Converts PDFs to images** for LLM vision processing
3. **Generates signed URLs** for secure, temporary file downloads

## Prerequisites

- Google Cloud Project (e.g., `YOUR_GCP_PROJECT_ID`)
- `gcloud` CLI installed and authenticated
- Appropriate GCP permissions (Storage Admin)

## Step 1: Create GCS Bucket

```bash
# Set your project ID
export GCP_PROJECT="YOUR_GCP_PROJECT_ID"

# Create bucket (choose a globally unique name)
export BUCKET_NAME="triage-attachments"
export REGION="us-east4"  # Same region as Cloud Run for better performance

gsutil mb -p ${GCP_PROJECT} -l ${REGION} -b on gs://${BUCKET_NAME}
```

**Bucket Configuration:**
- **Uniform bucket-level access**: Enabled (required for signed URLs)
- **Location**: Same region as your Cloud Run services
- **Storage class**: Standard (for frequently accessed files)

## Step 2: Configure IAM Permissions

The Cloud Run service account needs permission to:
- Upload files to the bucket
- Generate signed URLs for downloads

```bash
# Get your Cloud Run service account
# Default: PROJECT_NUMBER-compute@developer.gserviceaccount.com
# Or custom service account if you created one

export SERVICE_ACCOUNT="YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com"

# Grant Storage Object Admin permission
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:roles/storage.objectAdmin gs://${BUCKET_NAME}
```

## Step 3: Set Environment Variables

### Local Development (.env file)

```bash
# Add to backend/.env
GCS_ENABLED=true
GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID
GCS_BUCKET_NAME=triage-attachments
```

### Production (Cloud Run)

Update your Cloud Run services with the new environment variables:

```bash
# Update Backend API
gcloud run services update triage-api \
  --update-env-vars GCS_ENABLED=true \
  --update-env-vars GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID \
  --update-env-vars GCS_BUCKET_NAME=triage-attachments \
  --region us-east4

# Update Worker
gcloud run services update triage-worker \
  --update-env-vars GCS_ENABLED=true \
  --update-env-vars GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID \
  --update-env-vars GCS_BUCKET_NAME=triage-attachments \
  --region us-east4
```

## Step 4: Verify Setup

### Test Upload Locally

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Process a sample email (should upload attachments to GCS)
curl -X POST http://localhost:8000/emails/simulate-batch

# Check bucket contents
gsutil ls gs://${BUCKET_NAME}/cases/
```

### Test Download URL

```bash
# Get an attachment ID from the database
# Then test the download endpoint
curl -L http://localhost:8000/attachments/{attachment_id}/download
```

## Bucket Organization

Files are organized by case number for easy management:

```
gs://triage-attachments/
└── cases/
    ├── NF-39281/
    │   ├── Doe_J_Declaration.pdf
    │   └── Medical_Records.pdf
    ├── NF-39282/
    │   └── Cover_Letter.pdf
    └── ...
```

## Signed URL Expiration

- **Default expiration**: 60 minutes
- Modify in `backend/app/services/gcs_storage.py` if needed
- After expiration, user must click "View Full PDF" again to get a new URL

## Disabling GCS (Optional)

To disable GCS and store only metadata:

```bash
# Local: Set in .env
GCS_ENABLED=false

# Production: Update Cloud Run
gcloud run services update triage-api \
  --update-env-vars GCS_ENABLED=false \
  --region us-east4
```

When disabled:
- Attachments are still extracted and categorized
- Text previews and summaries are stored
- Full PDF files are NOT stored (only LLM-generated metadata)

## Cost Considerations

**Storage Costs** (us-east4 region):
- $0.020 per GB/month for Standard storage
- ~1-5 MB per PDF attachment
- Example: 1000 PDFs × 3 MB = ~$0.06/month

**Operations Costs**:
- Class A (uploads): $0.05 per 10,000 operations
- Class B (downloads): $0.004 per 10,000 operations
- Signed URL generation: Free (metadata operation)

**Total estimated cost for 1000 cases/month**: < $1

## Troubleshooting

### Error: "GCS client not initialized"

**Cause**: Missing credentials or incorrect project ID

**Solution**:
```bash
# Local development: Set application default credentials
gcloud auth application-default login

# Production: Verify service account has storage.objectAdmin role
gcloud projects get-iam-policy ${GCP_PROJECT} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT}"
```

### Error: "Failed to generate signed URL"

**Cause**: Service account lacks signBlob permission

**Solution**:
```bash
# Grant Service Account Token Creator role
gcloud projects add-iam-policy-binding ${GCP_PROJECT} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountTokenCreator"
```

### Files not appearing in bucket

**Cause**: GCS_ENABLED=false or upload failed silently

**Solution**:
1. Check environment variables: `GCS_ENABLED=true`
2. Check worker logs for upload errors:
   ```bash
   gcloud run services logs read triage-worker --limit 50 --region us-east4
   ```
3. Verify bucket name matches environment variable

### CORS errors in frontend

**Cause**: Signed URLs from GCS may trigger CORS if opened in iframe

**Solution**: The current implementation uses `target="_blank"` to open PDFs in a new tab, which avoids CORS issues. If you need iframe support, configure CORS on the bucket:

```bash
# Create cors.json
cat > cors.json << EOF
[
  {
    "origin": ["https://triage-ime.web.app", "http://localhost:5173"],
    "method": ["GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

# Apply CORS configuration
gsutil cors set cors.json gs://${BUCKET_NAME}
```

## Security Best Practices

1. **Use signed URLs**: Never make bucket public
2. **Short expiration**: Default 60 minutes is secure
3. **Uniform bucket access**: Required for signed URLs
4. **Service account isolation**: Use dedicated service account for storage
5. **Audit logs**: Enable Cloud Audit Logs for access monitoring

## Next Steps

- Set up lifecycle policies to archive old attachments
- Configure bucket versioning for data recovery
- Set up Cloud Monitoring alerts for storage quota
- Consider Cold/Archive storage class for long-term cases
