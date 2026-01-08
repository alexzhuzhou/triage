# Manual Deployment Guide (No GitHub Actions)

This guide shows how to deploy the Triage application **manually** without GitHub Actions CI/CD. This is simpler and requires fewer permissions.

---

## What You'll Do

1. ✅ Grant service account Secret Manager access (admin needed)
2. ✅ Deploy backend to Cloud Run (manual commands)
3. ✅ Deploy frontend to Firebase Hosting (manual commands)
4. ✅ Test the application

**No need for:**
- ❌ Workload Identity Federation
- ❌ GitHub secrets
- ❌ GitHub Actions workflows

---

## Prerequisites

### Completed Infrastructure (Already Done ✅)
- [x] Cloud SQL PostgreSQL (`triage-postgres`)
- [x] Memorystore Redis (`triage-redis`)
- [x] Artifact Registry (`triage-images`)
- [x] Service account (`triage-cloudsql-sa`)
- [x] Secret Manager secrets (`database-url`, `openai-api-key`)

### Tools Needed
- Google Cloud SDK (`gcloud`) - Already have ✅
- Docker - For building images
- Firebase CLI - `npm install -g firebase-tools`
- Node.js & npm - Already have ✅

---

## Step 1: Get Redis Host IP

Run in Google Cloud Shell:

```bash
gcloud redis instances describe triage-redis \
  --region=us-east4 \
  --format='value(host)'
```

**Save this IP** (e.g., `10.123.45.67`) - you'll use it in deployment commands.

---

## Step 2: Grant Service Account Secret Manager Access

**Ask your admin to run this command:**

```bash
gcloud projects add-iam-policy-binding premium-oven-394418 \
  --member="serviceAccount:triage-cloudsql-sa@premium-oven-394418.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

This allows the Cloud Run services to fetch `database-url` and `openai-api-key` from Secret Manager at startup.

**Verify it worked:**
```bash
gcloud projects get-iam-policy premium-oven-394418 \
  --flatten="bindings[].members" \
  --filter="bindings.members:triage-cloudsql-sa@premium-oven-394418.iam.gserviceaccount.com AND bindings.role:roles/secretmanager.secretAccessor"
```

Should show the binding.

---

## Step 3: Deploy Backend to Cloud Run

### A. Set Up Environment Variables

```bash
# Set these once
export GCP_PROJECT="premium-oven-394418"
export GCP_REGION="us-east4"
export REDIS_HOST="10.x.x.x"  # Replace with actual IP from Step 1
export SERVICE_ACCOUNT="triage-cloudsql-sa@premium-oven-394418.iam.gserviceaccount.com"
export CLOUD_SQL_CONNECTION="premium-oven-394418:us-east4:triage-postgres"
```

### B. Build and Push Docker Images

**Option 1: Build in Cloud Shell (Recommended - No local Docker needed)**

```bash
# Navigate to your project
cd ~/Triage/backend

# Build API image using Cloud Build
gcloud builds submit \
  --tag us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/api:latest \
  --timeout=20m \
  .

# Build Worker image using Cloud Build
gcloud builds submit \
  --tag us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  --timeout=20m \
  --dockerfile=Dockerfile.worker \
  .
```

**Option 2: Build Locally (If you have Docker installed)**

```bash
# Navigate to backend directory
cd backend

# Configure Docker for Artifact Registry
gcloud auth configure-docker us-east4-docker.pkg.dev

# Build API image
docker build \
  -f Dockerfile \
  -t us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/api:latest \
  .

# Build Worker image
docker build \
  -f Dockerfile.worker \
  -t us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  .

# Push images
docker push us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/api:latest
docker push us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest
```

### C. Deploy API Service

```bash
gcloud run deploy triage-api \
  --image=us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/api:latest \
  --platform=managed \
  --region=${GCP_REGION} \
  --service-account=${SERVICE_ACCOUNT} \
  --add-cloudsql-instances=${CLOUD_SQL_CONNECTION} \
  --set-env-vars="ENV=production,REDIS_URL=redis://${REDIS_HOST}:6379/0,ALLOWED_ORIGINS=http://localhost:5173,PDF_CONVERSION_ENABLED=true,PDF_CONVERSION_DPI=150,VISION_IMAGE_DETAIL=high,EMAIL_ENABLED=false,SIMULATE_LLM_FAILURES=false" \
  --cpu=1 \
  --memory=512Mi \
  --timeout=300 \
  --concurrency=80 \
  --min-instances=0 \
  --max-instances=10 \
  --allow-unauthenticated
```

When prompted "Allow unauthenticated invocations to [triage-api]?", answer **Y** (yes).

### D. Get API URL

```bash
API_URL=$(gcloud run services describe triage-api \
  --region=${GCP_REGION} \
  --format='value(status.url)')

echo "API URL: ${API_URL}"
```

**Save this URL** - you'll need it for the frontend and CORS configuration.

### E. Update CORS to Allow Firebase Hosting

You'll update this after setting up Firebase. For now, it allows localhost.

### F. Deploy Worker Service

```bash
gcloud run deploy triage-worker \
  --image=us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  --platform=managed \
  --region=${GCP_REGION} \
  --service-account=${SERVICE_ACCOUNT} \
  --add-cloudsql-instances=${CLOUD_SQL_CONNECTION} \
  --set-env-vars="ENV=production,REDIS_URL=redis://${REDIS_HOST}:6379/0,QUEUE_DEFAULT_TIMEOUT=600,QUEUE_RETRY_ATTEMPTS=5,PDF_CONVERSION_ENABLED=true,PDF_CONVERSION_DPI=150,VISION_IMAGE_DETAIL=high" \
  --cpu=1 \
  --memory=1Gi \
  --timeout=900 \
  --concurrency=1 \
  --min-instances=1 \
  --max-instances=3 \
  --no-allow-unauthenticated
```

When prompted about unauthenticated invocations, answer **N** (no) - the worker doesn't need public access.

### G. Test Backend

```bash
# Test API health
curl ${API_URL}/health

# Expected: {"status":"healthy"}

# Test queue status
curl ${API_URL}/queue/status

# Should show queue statistics
```

### H. Check Logs for Secret Manager

```bash
# View recent logs
gcloud run services logs read triage-api \
  --region=${GCP_REGION} \
  --limit=50

# Look for these success messages:
# ✅ Retrieved secret 'database-url' from Secret Manager
# ✅ Retrieved secret 'openai-api-key' from Secret Manager
```

If you see those messages, Secret Manager integration is working! ✅

---

## Step 4: Set Up Firebase

### A. Create or Connect Firebase Project

**Option 1: Create New Firebase Project**

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Enter project name (e.g., "Triage IME")
4. Disable Google Analytics (optional)
5. Click "Create project"

**Option 2: Add Firebase to Existing GCP Project (Recommended)**

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Select "Enter a project name"
4. In the dropdown, select **premium-oven-394418**
5. Click "Continue"
6. Confirm billing plan
7. Click "Add Firebase"

### B. Enable Firebase Hosting

1. In Firebase Console → Build → Hosting
2. Click "Get started"
3. Follow the wizard (we already have firebase.json, so you can skip CLI steps)

### C. Get Firebase Project ID

In Firebase Console → Project Settings (gear icon), you'll see:
- **Project ID**: `your-firebase-project-id` (save this)

### D. Update `.firebaserc` Locally

```bash
cd frontend

# Edit .firebaserc file
# Replace "your-firebase-project-id" with actual project ID
```

Or use this command:

```bash
# Replace YOUR_FIREBASE_PROJECT_ID with actual ID
cat > .firebaserc << EOF
{
  "projects": {
    "default": "YOUR_FIREBASE_PROJECT_ID"
  }
}
EOF
```

---

## Step 5: Deploy Frontend to Firebase Hosting

### A. Install Dependencies

```bash
cd frontend
npm install
```

### B. Create Production Environment File

```bash
# Replace API_URL_HERE with your actual API URL from Step 3D
echo "VITE_API_BASE_URL=${API_URL}" > .env.production

# Or manually:
echo "VITE_API_BASE_URL=https://triage-api-xxxxx-uk.a.run.app" > .env.production
```

### C. Build Production Bundle

```bash
npm run build
```

This creates the `dist/` folder with your production build.

### D. Install Firebase CLI (if not already installed)

```bash
npm install -g firebase-tools
```

### E. Login to Firebase

```bash
firebase login
```

This will open a browser for you to authenticate with Google.

### F. Deploy to Firebase Hosting

```bash
firebase deploy --only hosting
```

You'll see output like:

```
✔  Deploy complete!

Project Console: https://console.firebase.google.com/project/YOUR_PROJECT/overview
Hosting URL: https://your-project.web.app
```

**Save the Hosting URL** (e.g., `https://your-project.web.app`)

---

## Step 6: Update CORS for Production

Now that you have the Firebase Hosting URL, update the backend CORS configuration:

```bash
# Set your Firebase hosting URLs
FIREBASE_URL="https://your-project.web.app"
FIREBASE_URL_2="https://your-project.firebaseapp.com"

# Update API with new CORS origins
gcloud run services update triage-api \
  --region=${GCP_REGION} \
  --update-env-vars="ALLOWED_ORIGINS=${FIREBASE_URL},${FIREBASE_URL_2},http://localhost:5173"
```

---

## Step 7: Test End-to-End

### A. Open Frontend in Browser

Navigate to your Firebase Hosting URL: `https://your-project.web.app`

You should see the Triage dashboard.

### B. Test Email Processing

1. Click "Process" tab
2. Click "Process Batch" button
3. Wait for processing (watch the queue status)
4. Navigate to "Cases" tab
5. You should see cases appear!

### C. Verify Backend Logs

```bash
# Check API logs
gcloud run services logs read triage-api \
  --region=${GCP_REGION} \
  --limit=100

# Check Worker logs
gcloud run services logs read triage-worker \
  --region=${GCP_REGION} \
  --limit=100
```

Look for:
- ✅ Secret Manager retrieval messages
- Email processing logs
- LLM extraction calls
- Database operations

### D. Test Queue Dashboard

In the frontend:
1. Navigate to "Queue" tab
2. You should see queue statistics
3. Process some emails and watch the queue update

---

## Step 8: Future Deployments (Manual Process)

### When You Make Backend Changes

```bash
# 1. Navigate to backend directory
cd backend

# 2. Rebuild and deploy API (if API code changed)
gcloud builds submit \
  --tag us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/api:latest \
  .

gcloud run deploy triage-api \
  --image=us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/api:latest \
  --region=${GCP_REGION}

# 3. Rebuild and deploy Worker (if worker code changed)
gcloud builds submit \
  --tag us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  --dockerfile=Dockerfile.worker \
  .

gcloud run deploy triage-worker \
  --image=us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  --region=${GCP_REGION}
```

### When You Make Frontend Changes

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Rebuild and deploy
npm run build
firebase deploy --only hosting
```

---

## Useful Commands

### View Logs

```bash
# API logs (live tail)
gcloud run services logs tail triage-api --region=${GCP_REGION}

# Worker logs (live tail)
gcloud run services logs tail triage-worker --region=${GCP_REGION}

# View recent logs
gcloud run services logs read triage-api --region=${GCP_REGION} --limit=100
```

### Update Environment Variables

```bash
# Update single variable
gcloud run services update triage-api \
  --region=${GCP_REGION} \
  --update-env-vars="NEW_VAR=value"

# Update multiple variables
gcloud run services update triage-api \
  --region=${GCP_REGION} \
  --update-env-vars="VAR1=value1,VAR2=value2"
```

### View Service Status

```bash
# List all Cloud Run services
gcloud run services list --region=${GCP_REGION}

# Get detailed service info
gcloud run services describe triage-api --region=${GCP_REGION}
```

### Rollback Deployment

```bash
# List revisions
gcloud run revisions list --service=triage-api --region=${GCP_REGION}

# Route 100% traffic to previous revision
gcloud run services update-traffic triage-api \
  --region=${GCP_REGION} \
  --to-revisions=triage-api-00002-abc=100
```

### Check Secret Manager

```bash
# List secrets
gcloud secrets list

# View secret value
gcloud secrets versions access latest --secret=database-url

# Update a secret
echo -n "new-value" | gcloud secrets versions add database-url --data-file=-

# After updating secret, restart services to pick up new value
gcloud run services update triage-api --region=${GCP_REGION} --no-traffic
gcloud run services update triage-worker --region=${GCP_REGION} --no-traffic
```

---

## Troubleshooting

### Secret Manager Permission Denied

**Error:** `Permission 'secretmanager.secrets.access' denied`

**Solution:**
```bash
# Verify service account has accessor role
gcloud projects get-iam-policy premium-oven-394418 \
  --flatten="bindings[].members" \
  --filter="bindings.members:triage-cloudsql-sa@premium-oven-394418.iam.gserviceaccount.com"
```

Should show `roles/secretmanager.secretAccessor`. If not, ask admin to grant it (Step 2).

### Cloud Run Service Won't Start

**Check logs:**
```bash
gcloud run services logs read triage-api --region=${GCP_REGION} --limit=50
```

Common issues:
- **Database connection failed** → Check Cloud SQL connection name
- **Redis connection failed** → Check REDIS_HOST IP
- **Secret not found** → Verify secrets exist in Secret Manager

### CORS Errors in Browser

**Symptom:** Frontend can't connect to API, browser shows CORS error

**Solution:**
```bash
# Update ALLOWED_ORIGINS with your Firebase URL
gcloud run services update triage-api \
  --region=${GCP_REGION} \
  --update-env-vars="ALLOWED_ORIGINS=https://your-project.web.app,https://your-project.firebaseapp.com,http://localhost:5173"
```

### Frontend Shows Wrong API URL

**Check `.env.production`:**
```bash
cat frontend/.env.production
```

Should show:
```
VITE_API_BASE_URL=https://triage-api-xxxxx-uk.a.run.app
```

If wrong, update and rebuild:
```bash
echo "VITE_API_BASE_URL=${API_URL}" > frontend/.env.production
npm run build
firebase deploy --only hosting
```

---

## Cost Monitoring

Set up billing alerts to avoid unexpected charges:

1. Cloud Console → Billing → Budgets & alerts
2. Create budget for **$100/month**
3. Set alert thresholds at 50%, 90%, 100%
4. Add your email for notifications

**Estimated monthly cost: $65-90**

Breakdown:
- Cloud SQL: ~$30-40/month (db-f1-micro)
- Memorystore Redis: ~$25-30/month (1GB M1)
- Cloud Run: ~$5-10/month (serverless, pay-per-use)
- Firebase Hosting: Free tier (likely sufficient)
- Artifact Registry: ~$2-5/month (storage)

---

## Summary Checklist

- [ ] Get Redis host IP
- [ ] Grant service account Secret Manager access (admin)
- [ ] Build and push Docker images (API + Worker)
- [ ] Deploy API to Cloud Run
- [ ] Deploy Worker to Cloud Run
- [ ] Get API URL
- [ ] Set up Firebase project
- [ ] Update `.firebaserc` with project ID
- [ ] Build frontend with API URL
- [ ] Deploy frontend to Firebase Hosting
- [ ] Update CORS with Firebase URLs
- [ ] Test end-to-end (process emails, view cases)
- [ ] Verify Secret Manager in logs
- [ ] Set up billing alerts

**Once all checkboxes are complete, your application is fully deployed!**

---

## Next Steps (Optional)

After successful deployment, consider:

1. **Custom Domain** - Add your own domain to Firebase Hosting
2. **Monitoring** - Set up Cloud Monitoring dashboards
3. **Alerting** - Configure uptime checks and error alerts
4. **Backups** - Schedule automated database backups
5. **Staging Environment** - Create a separate staging project
6. **GitHub Actions** - Add CI/CD automation later if needed

---

## Comparison: Manual vs GitHub Actions

| Aspect | Manual Deployment | GitHub Actions |
|--------|------------------|----------------|
| Deployment | Run commands manually | Automatic on git push |
| Setup complexity | Simpler | More complex |
| Permissions needed | Just Secret Manager | Secret Manager + WIF |
| GitHub secrets | 0 | 8 secrets |
| Best for | Small teams, learning | Production, large teams |
| Control | Full control | Automated |

You can always add GitHub Actions later if you want automated deployments!