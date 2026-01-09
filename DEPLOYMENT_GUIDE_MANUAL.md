# Manual Deployment Guide (No GitHub Actions)

This guide shows how to deploy the Triage application **manually** without GitHub Actions CI/CD. This is simpler and requires fewer permissions.

**⚠️ Common Pitfalls to Avoid:**
- ❌ **Don't use `gcloud run services update --set-env-vars`** - it replaces ALL variables! Use `--update-env-vars` instead, or better yet, use Cloud Console UI
- ❌ **Don't skip VPC connector setup** - worker won't be able to connect to Redis without it
- ❌ **Don't use gcloud CLI for CORS** - comma escaping issues can break your config. Use Cloud Console UI
- ❌ **Don't forget to clear worker registration** before redeploying worker (see Troubleshooting section)
- ✅ **Do use repository name `triage-images`** not `triage`

---

## What You'll Do

1. ✅ Set up VPC networking for Redis access
2. ✅ Grant service account Secret Manager access (admin needed)
3. ✅ Deploy backend to Cloud Run (manual commands)
4. ✅ Deploy frontend to Firebase Hosting (manual commands)
5. ✅ Test the application

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
gcloud projects add-iam-policy-binding YOUR_GCP_PROJECT_ID \
  --member="serviceAccount:triage-cloudsql-sa@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

This allows the Cloud Run services to fetch `database-url` and `openai-api-key` from Secret Manager at startup.

**Verify it worked:**
```bash
gcloud projects get-iam-policy YOUR_GCP_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:triage-cloudsql-sa@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com AND bindings.role:roles/secretmanager.secretAccessor"
```

Should show the binding.

---

## Step 3: Set Up VPC Networking for Redis Access

The worker service needs to access Memorystore Redis, which has a private IP. We need to create a VPC connector.

### A. Enable VPC Access API

```bash
gcloud services enable vpcaccess.googleapis.com
```

### B. Create VPC Connector

```bash
gcloud compute networks vpc-access connectors create triage-connector \
  --region=us-east4 \
  --range=10.8.0.0/28 \
  --network=default
```

This creates a connector that allows Cloud Run services to access private resources (like Redis).

### C. Create Firewall Rule for Redis Access

```bash
gcloud compute firewall-rules create allow-vpc-connector-to-redis \
  --network=default \
  --direction=INGRESS \
  --priority=1000 \
  --source-ranges=10.8.0.0/28 \
  --destination-ranges=10.108.76.144/29 \
  --allow=tcp:6379 \
  --description="Allow VPC connector to access Memorystore Redis"
```

Replace `10.108.76.144/29` with your actual Redis IP range (check with `gcloud redis instances describe triage-redis --region=us-east4 --format='value(reservedIpRange)'`).

---

## Step 4: Deploy Backend to Cloud Run

### A. Set Up Environment Variables

```bash
# Set these once
export GCP_PROJECT="YOUR_GCP_PROJECT_ID"
export GCP_REGION="us-east4"
export REDIS_HOST="10.x.x.x"  # Replace with actual IP from Step 1
export SERVICE_ACCOUNT="triage-cloudsql-sa@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com"
export CLOUD_SQL_CONNECTION="YOUR_GCP_PROJECT_ID:us-east4:triage-postgres"
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

# Build Worker image - gcloud builds submit doesn't support --dockerfile flag
# So we use Docker directly in Cloud Shell
docker build -f Dockerfile.worker \
  -t us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  .

docker push us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest
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

**IMPORTANT:** Worker needs VPC connector to access Redis.

```bash
gcloud run deploy triage-worker \
  --image=us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  --platform=managed \
  --region=${GCP_REGION} \
  --service-account=${SERVICE_ACCOUNT} \
  --add-cloudsql-instances=${CLOUD_SQL_CONNECTION} \
  --vpc-connector=triage-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars="ENV=production,REDIS_URL=redis://${REDIS_HOST}:6379/0,QUEUE_DEFAULT_TIMEOUT=600,QUEUE_RETRY_ATTEMPTS=5,PDF_CONVERSION_ENABLED=true,PDF_CONVERSION_DPI=150,VISION_IMAGE_DETAIL=high" \
  --cpu=1 \
  --memory=1Gi \
  --timeout=900 \
  --concurrency=1 \
  --min-instances=1 \
  --max-instances=3 \
  --no-allow-unauthenticated
```

**Key flags:**
- `--vpc-connector=triage-connector` - Allows worker to access private Redis
- `--vpc-egress=private-ranges-only` - Routes only private IPs through VPC connector (saves cost)

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

## Step 5: Set Up Firebase Hosting

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
4. In the dropdown, select **YOUR_GCP_PROJECT_ID**
5. Click "Continue"
6. Confirm billing plan
7. Click "Add Firebase"

### B. Create Firebase Hosting Site

**IMPORTANT:** If you already have apps hosted on this Firebase project, create a new site:

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Create a new hosting site (for multi-site hosting)
firebase hosting:sites:create triage-ime --project=YOUR_GCP_PROJECT_ID
```

This creates a dedicated site: `https://triage-ime.web.app`

### C. Update `.firebaserc` for Multi-Site Hosting

```bash
cd frontend

# Create .firebaserc with multi-site configuration
cat > .firebaserc << 'EOF'
{
  "projects": {
    "default": "YOUR_GCP_PROJECT_ID"
  },
  "targets": {
    "YOUR_GCP_PROJECT_ID": {
      "hosting": {
        "triage": ["triage-ime"]
      }
    }
  }
}
EOF
```

### D. Update `firebase.json` to Use Target

```bash
# Update firebase.json to use the target
cat > firebase.json << 'EOF'
{
  "hosting": {
    "target": "triage",
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
EOF
```

---

## Step 6: Deploy Frontend to Firebase Hosting

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

## Step 7: Update CORS for Production

Now that you have the Firebase Hosting URL, update the backend CORS configuration.

**⚠️ IMPORTANT:** Use the Cloud Console UI to update CORS, NOT gcloud CLI. The CLI has issues with comma escaping that can break your environment variables.

### Update CORS via Cloud Console (Recommended)

1. Go to [Cloud Run Console](https://console.cloud.google.com/run?project=YOUR_GCP_PROJECT_ID)
2. Click **triage-api** service
3. Click **EDIT & DEPLOY NEW REVISION** at the top
4. Scroll to **Container → Variables & Secrets**
5. Find `ALLOWED_ORIGINS` and click Edit
6. Update value to:
   ```
   https://triage-ime.web.app,https://triage-ime.firebaseapp.com,http://localhost:5173
   ```
7. Click **DEPLOY**

### Alternative: Update via gcloud CLI (Advanced)

If you must use CLI, be very careful with escaping:

```bash
# This works on Linux/Mac, may fail on Windows
gcloud run services update triage-api \
  --region=us-east4 \
  --set-env-vars="^@^ALLOWED_ORIGINS=https://triage-ime.web.app,https://triage-ime.firebaseapp.com,http://localhost:5173"
```

**Note:** If the CLI command fails or removes other environment variables, use the Cloud Console method instead.

---

## Step 8: Test End-to-End

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

## Step 9: Future Deployments (Manual Process)

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
# NOTE: See "Worker Redeployment Issue" below if deployment fails

docker build -f Dockerfile.worker \
  -t us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  .

docker push us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest

# Before deploying worker, clear Redis worker registration to avoid conflicts
curl -X POST ${API_URL}/queue/admin/clear-workers

# Now deploy the worker
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

# View logs for specific revision (useful if latest revision failed)
# First, list revisions to find the working one
gcloud run revisions list --service=triage-worker --region=${GCP_REGION}

# Then view logs for that specific revision
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=triage-worker AND resource.labels.revision_name=triage-worker-00002-c2x" \
  --limit=50 \
  --format="table(timestamp,textPayload)"
```

### Update Environment Variables

```bash
# ⚠️ IMPORTANT: Always use --update-env-vars (NOT --set-env-vars)
# --set-env-vars REPLACES all variables, --update-env-vars modifies specific ones

# Update single variable
gcloud run services update triage-api \
  --region=${GCP_REGION} \
  --update-env-vars="NEW_VAR=value"

# Update multiple variables (be careful with comma escaping!)
# RECOMMENDED: Use Cloud Console UI instead for comma-separated values
gcloud run services update triage-api \
  --region=${GCP_REGION} \
  --update-env-vars="VAR1=value1,VAR2=value2"
```

### Manage Worker Registrations

```bash
# Check queue health and worker status
curl ${API_URL}/queue/health | python3 -m json.tool

# Clear worker registrations before redeploying worker
# This prevents "worker already exists" errors
curl -X POST ${API_URL}/queue/admin/clear-workers | python3 -m json.tool

# View queue status
curl ${API_URL}/queue/status | python3 -m json.tool

# View failed jobs
curl ${API_URL}/queue/failed-jobs | python3 -m json.tool
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

### Worker Redeployment Issue: "worker already exists"

**Error:** `ValueError: There exists an active worker named 'worker-production' already`

**Cause:** The current worker is registered in Redis. New deployments can't start because Redis sees an active worker with the same name.

**Solution:**
```bash
# Clear worker registrations from Redis before redeploying
curl -X POST https://YOUR-API-URL.run.app/queue/admin/clear-workers

# Now redeploy the worker
gcloud run deploy triage-worker \
  --image=us-east4-docker.pkg.dev/${GCP_PROJECT}/triage-images/worker:latest \
  --region=${GCP_REGION}
```

### Worker Can't Connect to Redis: Timeout Error

**Error:** `TimeoutError: Timeout connecting to server` in worker logs

**Cause:** Worker doesn't have VPC connector configured, can't access private Redis IP.

**Solution:**
```bash
# Add VPC connector to worker
gcloud run services update triage-worker \
  --region=${GCP_REGION} \
  --vpc-connector=triage-connector \
  --vpc-egress=private-ranges-only
```

### Viewing Logs for Specific Revision

**Problem:** Cloud Console shows latest (failed) revision logs by default.

**Solution 1 - Cloud Console:**
1. Go to Cloud Run → triage-worker → LOGS tab
2. Click the revision dropdown at the top
3. Select the working revision (e.g., `triage-worker-00002-c2x`)

**Solution 2 - Direct URL:**
Replace `REVISION_NAME` with your working revision:
```
https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%22triage-worker%22%0Aresource.labels.revision_name%3D%22REVISION_NAME%22?project=YOUR_GCP_PROJECT_ID
```

**Solution 3 - gcloud CLI:**
```bash
# List revisions to find the working one
gcloud run revisions list --service=triage-worker --region=${GCP_REGION}

# View logs for specific revision (replace REVISION_NAME)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=triage-worker AND resource.labels.revision_name=REVISION_NAME" \
  --limit=50 \
  --format="table(timestamp,textPayload)"
```

### Secret Manager Permission Denied

**Error:** `Permission 'secretmanager.secrets.access' denied`

**Solution:**
```bash
# Verify service account has accessor role
gcloud projects get-iam-policy YOUR_GCP_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:triage-cloudsql-sa@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com"
```

Should show `roles/secretmanager.secretAccessor`. If not, ask admin to grant it (Step 2).

### Cloud Run Service Won't Start

**Check logs:**
```bash
gcloud run services logs read triage-api --region=${GCP_REGION} --limit=50
```

Common issues:
- **Database connection failed** → Check Cloud SQL connection name
- **Redis connection failed** → Check REDIS_HOST IP and VPC connector
- **Secret not found** → Verify secrets exist in Secret Manager
- **Health check timeout** → Check if service listens on PORT=8080

### CORS Errors in Browser

**Symptom:** Frontend can't connect to API, browser shows CORS error

**Solution:** Use Cloud Console UI (Step 7) to update ALLOWED_ORIGINS. **Do NOT use gcloud CLI** - it has escaping issues that can break your environment variables.

### CORS Update Removed Other Environment Variables

**Problem:** After running `gcloud run services update --set-env-vars`, other environment variables disappeared.

**Cause:** `--set-env-vars` **replaces all** environment variables, not just the ones you specify.

**Solution:** Always use `--update-env-vars` to modify individual variables, or use the Cloud Console UI.

### Environment Variable Escaping Issues with gcloud

**Problem:** Comma-separated values in environment variables get mangled by gcloud CLI.

**Solution:** Use the Cloud Console UI to edit environment variables instead of CLI. See Step 7 for instructions.

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

### Email Polling Causes Startup Timeout

**Error:** Container failed to start when EMAIL_ENABLED=true

**Cause:** IMAP connection blocks startup health check

**Solution:** Set EMAIL_ENABLED=false for automatic polling. Use manual poll endpoint instead:
```bash
curl -X POST ${API_URL}/email-polling/manual-poll -H "Content-Type: application/json" -d '{}'
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
- [ ] Enable VPC Access API
- [ ] Create VPC connector (triage-connector)
- [ ] Create firewall rule for Redis access
- [ ] Build and push Docker images (API + Worker)
- [ ] Deploy API to Cloud Run
- [ ] Deploy Worker to Cloud Run with VPC connector
- [ ] Get API URL
- [ ] Set up Firebase project
- [ ] Create Firebase Hosting site (triage-ime)
- [ ] Update `.firebaserc` for multi-site hosting
- [ ] Update `firebase.json` with target
- [ ] Build frontend with API URL
- [ ] Deploy frontend to Firebase Hosting
- [ ] Update CORS with Firebase URLs (use Cloud Console UI)
- [ ] Test end-to-end (process emails, view cases)
- [ ] Verify Secret Manager in logs
- [ ] Verify worker can connect to Redis
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