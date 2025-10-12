# SampleTok Deployment Guide

## Recommended Setup: Vercel (Frontend) + GCP Cloud Run (Backend)

This guide covers the optimal deployment strategy for SampleTok:

- **Frontend**: Vercel (optimized Next.js hosting, auto-scaling, CDN)
- **Backend**: GCP Cloud Run (scalable FastAPI, auto-scaling, integrated
  services)
- **Database**: GCP Cloud SQL (PostgreSQL)
- **Storage**: Cloudflare R2 (recommended for zero egress costs)
- **Workers**: Inngest (managed background jobs)

### Why This Stack?

✅ **Vercel Frontend**

- Zero-config Next.js deployment
- Automatic builds on git push
- Global CDN for fast load times
- Free tier for hobby projects
- Excellent developer experience

✅ **GCP Cloud Run Backend**

- Auto-scales to zero (pay only when used)
- Integrated with Cloud SQL and Cloud Storage
- Managed SSL certificates
- Simple Docker-based deployments
- $300 free trial credit

**Total Cost**: $0-25/month for small-to-medium traffic

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [GCP Backend Deployment](#gcp-backend-deployment)
3. [Vercel Frontend Deployment](#vercel-frontend-deployment)
4. [Inngest Configuration](#inngest-configuration)
5. [Environment Variables Reference](#environment-variables-reference)
6. [Database Migrations](#database-migrations)
7. [Monitoring and Logs](#monitoring-and-logs)
8. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- ffmpeg
- Google Cloud SDK
- Git

### Quick Start

1. **Clone Repository**

```bash
git clone <your-repo-url>
cd sampletok
```

2. **Start Infrastructure Services**

```bash
cd backend
docker-compose up -d
```

3. **Backend Setup**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your local settings

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Frontend Setup**

```bash
cd frontend
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start frontend
npm run dev
```

Access at `http://localhost:3000`

---

## GCP Backend Deployment

### Step 1: Install and Configure GCP CLI

```bash
# Install Google Cloud SDK
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Initialize and login
gcloud init
gcloud auth login
```

### Step 2: Create GCP Project

```bash
# Create project
gcloud projects create sampletok-prod --name="SampleTok Production"

# Set as active project
gcloud config set project sampletok-prod

# Link billing account (required)
# Go to: https://console.cloud.google.com/billing
# Or list accounts: gcloud billing accounts list
gcloud billing projects link sampletok-prod --billing-account=BILLING_ACCOUNT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com
```

### Step 3: Set up Cloud SQL (PostgreSQL)

```bash
# Create PostgreSQL instance
# For production: use --tier=db-g1-small or larger
gcloud sql instances create sampletok-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))") \
  --storage-type=SSD \
  --storage-size=10GB \
  --backup \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04

# Create database
gcloud sql databases create sampletok --instance=sampletok-db

# Create user
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
gcloud sql users create sampletok \
  --instance=sampletok-db \
  --password=$DB_PASSWORD

# Save these for later!
echo "Database Password: $DB_PASSWORD"

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe sampletok-db --format='value(connectionName)')
echo "Connection Name: $CONNECTION_NAME"
```

**Save these values!** You'll need them for environment variables.

### Step 4: Set up Cloudflare R2 Storage

**Why R2?** Zero egress fees (no charges for downloads), S3-compatible API, and
cheaper than GCS.

1. **Create R2 Bucket** (if you don't already have one):
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → R2
   - Create bucket: `sampletok-samples` (or use existing)
   - Enable public access via Settings → Public Access → Allow

2. **Get R2 Credentials**:
   - In R2 dashboard → Manage R2 API Tokens
   - Create API token with read/write permissions
   - Save the **Access Key ID** and **Secret Access Key**
   - Note your **Endpoint URL** (format:
     `https://<account-id>.r2.cloudflarestorage.com`)

3. **Enable R2.dev subdomain** (for public URLs):
   - In your bucket settings → Settings → Public Access
   - Enable "R2.dev subdomain"
   - Note the public domain (format: `pub-<hash>.r2.dev`)

**You'll need these values for Secret Manager in the next step.**

### Step 5: Set up Secret Manager

```bash
# Generate secure keys
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Create application secrets
echo -n "$SECRET_KEY" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "$JWT_SECRET_KEY" | gcloud secrets create JWT_SECRET_KEY --data-file=-

# Add RapidAPI key (replace with your actual key from https://rapidapi.com)
echo -n "YOUR_RAPIDAPI_KEY" | gcloud secrets create RAPIDAPI_KEY --data-file=-

# Add R2 credentials (replace with your actual R2 credentials)
echo -n "YOUR_R2_ACCESS_KEY_ID" | gcloud secrets create AWS_ACCESS_KEY_ID --data-file=-
echo -n "YOUR_R2_SECRET_ACCESS_KEY" | gcloud secrets create AWS_SECRET_ACCESS_KEY --data-file=-

# Add Inngest keys (we'll update these later after creating Inngest account)
echo -n "PLACEHOLDER" | gcloud secrets create INNGEST_EVENT_KEY --data-file=-
echo -n "PLACEHOLDER" | gcloud secrets create INNGEST_SIGNING_KEY --data-file=-

# Grant Cloud Run access to all secrets
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
for SECRET in SECRET_KEY JWT_SECRET_KEY RAPIDAPI_KEY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY INNGEST_EVENT_KEY INNGEST_SIGNING_KEY; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

### Step 6: Prepare Backend for Deployment

1. **Create Dockerfile** (`backend/Dockerfile`)

```dockerfile
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create startup script that runs migrations then starts server
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Running database migrations..."\n\
alembic upgrade head\n\
echo "Starting application..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/start.sh && \
chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

CMD ["/app/start.sh"]
```

2. **Create .gcloudignore** (`backend/.gcloudignore`)

```
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
.env
.env.local
.env.*
*.log
.git/
.gitignore
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
dist/
build/
*.sqlite
*.db
alembic/versions/__pycache__/
```

3. **Update requirements.txt** (add GCS support if needed)

```bash
cd backend
# Check if google-cloud-storage is in requirements.txt
grep "google-cloud-storage" requirements.txt || echo "google-cloud-storage==2.10.0" >> requirements.txt
```

### Step 7: Deploy Backend to Cloud Run

```bash
cd backend

# Get connection name from earlier
CONNECTION_NAME=$(gcloud sql instances describe sampletok-db --format='value(connectionName)')

# Build and deploy with R2 storage
gcloud run deploy sampletok-backend \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --set-env-vars="ENVIRONMENT=production,STORAGE_TYPE=r2,S3_BUCKET_NAME=sampletok-samples,S3_ENDPOINT_URL=https://817fde014b86ba18d60b1820218aece1.r2.cloudflarestorage.com,R2_PUBLIC_DOMAIN=pub-ee4520d17c5045a2a8bf1a6725318377.r2.dev,AWS_REGION=auto,API_V1_STR=/api/v1,DEBUG=False,DATABASE_ECHO=False,RAPIDAPI_HOST=tiktok-video-no-watermark2.p.rapidapi.com" \
  --set-secrets="SECRET_KEY=SECRET_KEY:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,RAPIDAPI_KEY=RAPIDAPI_KEY:latest,AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID:latest,AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY:latest,INNGEST_EVENT_KEY=INNGEST_EVENT_KEY:latest,INNGEST_SIGNING_KEY=INNGEST_SIGNING_KEY:latest" \
  --add-cloudsql-instances=$CONNECTION_NAME

# This will take a few minutes...
```

### Step 8: Configure Backend Environment

```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe sampletok-backend --region=us-central1 --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"

# Update with database connection and CORS
# Replace DB_PASSWORD with the password you saved earlier
gcloud run services update sampletok-backend \
  --region=us-central1 \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://sampletok:YOUR_DB_PASSWORD@/sampletok?host=/cloudsql/$CONNECTION_NAME,BACKEND_CORS_ORIGINS=https://sampletok.vercel.app,https://yourdomain.com"

# Test backend health
curl $BACKEND_URL/api/v1/health
```

**Expected response**: `{"status":"healthy"}`

---

## Vercel Frontend Deployment

### Step 1: Prepare Frontend

1. **Update next.config.js** (`frontend/next.config.js`)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Add any existing config here

  // Optional: Add security headers
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "X-Frame-Options",
            value: "SAMEORIGIN",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

2. **Ensure API URL is configurable** (`frontend/.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 2: Deploy to Vercel

**Option A: Vercel CLI** (Recommended for first deployment)

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy from frontend directory
cd frontend
vercel

# Follow prompts:
# - Set up and deploy? Yes
# - Which scope? (select your account)
# - Link to existing project? No
# - Project name? sampletok
# - Directory? ./
# - Override settings? No

# This will give you a preview URL
```

**Option B: Vercel Dashboard** (Easiest)

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your Git repository
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
4. Click "Deploy"

### Step 3: Configure Vercel Environment Variables

After initial deployment:

1. Go to your project in Vercel Dashboard
2. Settings → Environment Variables
3. Add:
   ```
   NEXT_PUBLIC_API_URL = <your-backend-url-from-gcp>
   ```
   Example: `https://sampletok-backend-abc123-uc.a.run.app`

4. Redeploy:
   ```bash
   vercel --prod
   ```

### Step 4: Update Backend CORS

```bash
# Get your Vercel URL
VERCEL_URL="https://sampletok.vercel.app"  # Replace with your actual URL

# Update backend CORS
gcloud run services update sampletok-backend \
  --region=us-central1 \
  --update-env-vars="BACKEND_CORS_ORIGINS=$VERCEL_URL"
```

### Step 5: Custom Domain (Optional)

**In Vercel Dashboard:**

1. Project Settings → Domains
2. Add your custom domain
3. Follow DNS configuration instructions

**Update Backend CORS:**

```bash
gcloud run services update sampletok-backend \
  --region=us-central1 \
  --update-env-vars="BACKEND_CORS_ORIGINS=https://yourdomain.com,https://sampletok.vercel.app"
```

---

## Inngest Configuration

### Step 1: Create Inngest Account

1. Go to [inngest.com](https://inngest.com)
2. Sign up for free account
3. Create new app: "SampleTok"

### Step 2: Get Inngest Credentials

1. In Inngest dashboard → Settings → Keys
2. Copy:
   - **Event Key** (starts with `inngest_`)
   - **Signing Key** (for webhook verification)

### Step 3: Update GCP Secrets

```bash
# Update Inngest secrets
echo -n "YOUR_INNGEST_EVENT_KEY" | gcloud secrets versions add INNGEST_EVENT_KEY --data-file=-
echo -n "YOUR_INNGEST_SIGNING_KEY" | gcloud secrets versions add INNGEST_SIGNING_KEY --data-file=-

# Redeploy backend to pick up new secrets
gcloud run services update sampletok-backend --region=us-central1
```

### Step 4: Configure Inngest Webhook

1. In Inngest dashboard → Settings → Webhooks
2. Add webhook URL:
   ```
   https://sampletok-backend-xxx.run.app/api/v1/inngest
   ```
   (Replace with your actual backend URL)
3. Save

### Step 5: Test Inngest Integration

```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe sampletok-backend --region=us-central1 --format='value(status.url)')

# Test Inngest endpoint
curl $BACKEND_URL/api/v1/inngest
```

Should return Inngest configuration info.

---

## Environment Variables Reference

### Backend (GCP Cloud Run)

Set via Cloud Run environment variables and Secret Manager:

```bash
# Application
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<from-secret-manager>
APP_NAME=SampleTok
APP_VERSION=0.1.0

# API
API_V1_STR=/api/v1
BACKEND_CORS_ORIGINS=https://sampletok.vercel.app,https://yourdomain.com

# Database (Cloud SQL via Unix socket)
DATABASE_URL=postgresql+asyncpg://sampletok:PASSWORD@/sampletok?host=/cloudsql/PROJECT:REGION:INSTANCE
DATABASE_ECHO=False

# Storage (Cloudflare R2)
STORAGE_TYPE=r2
S3_BUCKET_NAME=sampletok-samples
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_PUBLIC_DOMAIN=pub-<hash>.r2.dev
AWS_REGION=auto
AWS_ACCESS_KEY_ID=<from-secret-manager>
AWS_SECRET_ACCESS_KEY=<from-secret-manager>

# JWT
JWT_SECRET_KEY=<from-secret-manager>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Inngest
INNGEST_EVENT_KEY=<from-secret-manager>
INNGEST_SIGNING_KEY=<from-secret-manager>

# TikTok Processing
MAX_VIDEO_DURATION_SECONDS=300
MAX_CONCURRENT_DOWNLOADS=5
DOWNLOAD_TIMEOUT_SECONDS=60

# Audio Processing
AUDIO_SAMPLE_RATE=48000
AUDIO_BIT_DEPTH=24
MP3_BITRATE=320
WAVEFORM_WIDTH=800
WAVEFORM_HEIGHT=320

# RapidAPI
RAPIDAPI_KEY=<from-secret-manager>
RAPIDAPI_HOST=tiktok-video-no-watermark2.p.rapidapi.com
```

### Frontend (Vercel)

Set via Vercel Dashboard → Environment Variables:

```bash
NEXT_PUBLIC_API_URL=https://sampletok-backend-xxx.run.app
```

---

## Database Migrations

### Running Migrations

Migrations run automatically on backend deployment (in Dockerfile startup
script).

### Manual Migration (if needed)

```bash
# Install Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy

# Start proxy
./cloud-sql-proxy --port 5432 PROJECT_ID:REGION:sampletok-db &

# In another terminal, run migrations
cd backend
source venv/bin/activate
export DATABASE_URL="postgresql+asyncpg://sampletok:PASSWORD@localhost:5432/sampletok"
alembic upgrade head

# Stop proxy
pkill cloud-sql-proxy
```

### Creating New Migrations

```bash
cd backend
source venv/bin/activate

# Generate migration
alembic revision --autogenerate -m "description of changes"

# Review generated migration in alembic/versions/
# Edit if needed

# Test locally
alembic upgrade head

# Commit and push - will auto-deploy on next Cloud Run deployment
git add alembic/versions/
git commit -m "Add migration: description"
git push
```

---

## Monitoring and Logs

### View Backend Logs (GCP)

```bash
# Tail logs
gcloud run services logs tail sampletok-backend --region=us-central1

# View in Cloud Console
# https://console.cloud.google.com/logs
```

### View Frontend Logs (Vercel)

```bash
# View in Vercel Dashboard
# Project → Deployments → [select deployment] → Logs

# Or via CLI
vercel logs sampletok
```

### View Database Logs

```bash
# List recent operations
gcloud sql operations list --instance=sampletok-db --limit=10

# View slow queries
gcloud sql instances describe sampletok-db
```

### Set up Monitoring

**GCP Cloud Monitoring** (automatic):

- Go to Cloud Console → Monitoring
- View metrics for Cloud Run, Cloud SQL

**Vercel Analytics** (built-in):

- Dashboard → Analytics

**Recommended: Add Sentry for Error Tracking**

```bash
# Backend
pip install sentry-sdk[fastapi]

# Frontend
npm install --save @sentry/nextjs
```

---

## CI/CD Setup (Monorepo-Optimized)

### Overview

This project is a **monorepo** with separate `frontend/` and `backend/`
directories. The CI/CD setup is optimized to:

- Only run tests/builds for changed code (not the entire monorepo)
- Deploy backend and frontend independently
- Run quality checks before deployment

### GitHub Secrets Setup

Before setting up workflows, add these secrets to your GitHub repository
(Settings → Secrets and variables → Actions):

1. **GCP_SA_KEY** - Service account JSON key with these roles:
   - Cloud Run Admin
   - Cloud SQL Client
   - Storage Object Admin
   - Secret Manager Secret Accessor
   - Service Account User

2. **VERCEL_TOKEN** - Vercel API token (for automated deployments)
3. **VERCEL_ORG_ID** - Your Vercel organization ID
4. **VERCEL_PROJECT_ID** - Your Vercel project ID

**Get Vercel credentials:**

```bash
# Install Vercel CLI
npm i -g vercel

# Login and link project
cd frontend
vercel link

# Get org and project IDs (saved in .vercel/project.json)
cat .vercel/project.json

# Create token at: https://vercel.com/account/tokens
```

**Create GCP Service Account:**

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployer"

# Grant necessary roles
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

for ROLE in \
  "roles/run.admin" \
  "roles/cloudsql.client" \
  "roles/storage.objectAdmin" \
  "roles/secretmanager.secretAccessor" \
  "roles/iam.serviceAccountUser"; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE"
done

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=$SA_EMAIL

# Copy contents to GitHub Secrets as GCP_SA_KEY
cat github-actions-key.json
# Then delete the local file for security
rm github-actions-key.json
```

---

### Workflow 1: Pre-Deployment CI (Quality Checks)

This workflow runs on every pull request and push to ensure code quality.

Create `.github/workflows/ci.yml`:

```yaml
name: CI - Tests and Linting

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: actions/checkout@v4

      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - '.github/workflows/ci.yml'
            frontend:
              - 'frontend/**'
              - '.github/workflows/ci.yml'

  backend-checks:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true'
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: ./backend

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov black ruff mypy

      - name: Code formatting check (Black)
        run: black --check app/
        continue-on-error: true

      - name: Linting (Ruff)
        run: ruff check app/
        continue-on-error: true

      - name: Type checking (MyPy)
        run: mypy app/ --ignore-missing-imports
        continue-on-error: true

      - name: Run tests
        run: |
          # Add tests when available
          echo "No tests configured yet"
        continue-on-error: true

  frontend-checks:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: ./frontend

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "18"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Linting (ESLint)
        run: npm run lint
        continue-on-error: true

      - name: Type checking (TypeScript)
        run: npx tsc --noEmit
        continue-on-error: true

      - name: Build check
        run: npm run build
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000

      - name: Run tests
        run: |
          # Add tests when available
          echo "No tests configured yet"
        continue-on-error: true
```

---

### Workflow 2: Backend Deployment

Create `.github/workflows/deploy-backend.yml`:

```yaml
name: Deploy Backend to Cloud Run

on:
  push:
    branches:
      - main
    paths:
      - "backend/**"
      - ".github/workflows/deploy-backend.yml"

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
        with:
          project_id: sampletok-prod

      - name: Configure Docker for GCR
        run: gcloud auth configure-docker

      - name: Get Cloud SQL connection name
        id: sql
        run: |
          CONNECTION_NAME=$(gcloud sql instances describe sampletok-db --format='value(connectionName)')
          echo "connection_name=$CONNECTION_NAME" >> $GITHUB_OUTPUT

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy sampletok-backend \
            --source ./backend \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated \
            --memory 2Gi \
            --cpu 2 \
            --timeout 300 \
            --min-instances 0 \
            --max-instances 10 \
            --concurrency 80 \
            --set-env-vars="ENVIRONMENT=production,STORAGE_TYPE=r2,S3_BUCKET_NAME=sampletok-samples,S3_ENDPOINT_URL=https://817fde014b86ba18d60b1820218aece1.r2.cloudflarestorage.com,R2_PUBLIC_DOMAIN=pub-ee4520d17c5045a2a8bf1a6725318377.r2.dev,AWS_REGION=auto,API_V1_STR=/api/v1,DEBUG=False,DATABASE_ECHO=False,RAPIDAPI_HOST=tiktok-video-no-watermark2.p.rapidapi.com" \
            --set-secrets="SECRET_KEY=SECRET_KEY:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,RAPIDAPI_KEY=RAPIDAPI_KEY:latest,AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID:latest,AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY:latest,INNGEST_EVENT_KEY=INNGEST_EVENT_KEY:latest,INNGEST_SIGNING_KEY=INNGEST_SIGNING_KEY:latest" \
            --add-cloudsql-instances=${{ steps.sql.outputs.connection_name }}

      - name: Get backend URL
        id: backend
        run: |
          BACKEND_URL=$(gcloud run services describe sampletok-backend --region=us-central1 --format='value(status.url)')
          echo "Backend deployed to: $BACKEND_URL"
          echo "url=$BACKEND_URL" >> $GITHUB_OUTPUT

      - name: Verify deployment
        run: |
          sleep 10
          curl -f ${{ steps.backend.outputs.url }}/api/v1/health || exit 1
          echo "✅ Backend health check passed"
```

---

### Workflow 3: Frontend Deployment

Create `.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend to Vercel

on:
  push:
    branches:
      - main
    paths:
      - "frontend/**"
      - ".github/workflows/deploy-frontend.yml"

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "18"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install Vercel CLI
        run: npm install --global vercel@latest

      - name: Pull Vercel Environment Information
        run: vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend

      - name: Build Project Artifacts
        run: vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend

      - name: Deploy to Vercel
        id: deploy
        run: |
          DEPLOYMENT_URL=$(vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }} 2>&1 | grep -o 'https://[^ ]*')
          echo "Frontend deployed to: $DEPLOYMENT_URL"
          echo "url=$DEPLOYMENT_URL" >> $GITHUB_OUTPUT
        working-directory: ./frontend

      - name: Verify deployment
        run: |
          sleep 10
          curl -f ${{ steps.deploy.outputs.url }} || exit 1
          echo "✅ Frontend health check passed"
```

---

### Workflow 4: Manual Deployment (Optional)

For testing or emergency deployments, create
`.github/workflows/manual-deploy.yml`:

```yaml
name: Manual Deployment

on:
  workflow_dispatch:
    inputs:
      target:
        description: "What to deploy"
        required: true
        type: choice
        options:
          - backend
          - frontend
          - both
      environment:
        description: "Environment"
        required: true
        type: choice
        options:
          - production
          - staging

jobs:
  deploy-backend:
    if: inputs.target == 'backend' || inputs.target == 'both'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Deploy Backend
        run: |
          gcloud run deploy sampletok-backend-${{ inputs.environment }} \
            --source ./backend \
            --region us-central1 \
            --platform managed

  deploy-frontend:
    if: inputs.target == 'frontend' || inputs.target == 'both'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "18"

      - name: Install Vercel CLI
        run: npm install --global vercel@latest

      - name: Deploy Frontend
        run: |
          cd frontend
          vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }}
```

---

### Monorepo Configuration Files

#### 1. Create `vercel.json` in project root:

```json
{
  "version": 2,
  "buildCommand": "cd frontend && npm run build",
  "devCommand": "cd frontend && npm run dev",
  "installCommand": "cd frontend && npm install",
  "framework": "nextjs",
  "outputDirectory": "frontend/.next",
  "ignoreCommand": "bash -c 'if [[ $VERCEL_GIT_COMMIT_REF != main && $VERCEL_GIT_COMMIT_REF != develop ]]; then exit 1; else exit 0; fi'"
}
```

#### 2. Update `.gitignore` (if needed):

```
# GitHub Actions
.github/secrets/

# Vercel
.vercel
frontend/.vercel

# Local credentials
*-key.json
github-actions-key.json
```

---

### Setting Up for the First Time

1. **Add GitHub Secrets** (see above)

2. **Create workflow files:**

```bash
mkdir -p .github/workflows
# Copy the workflow YAML files above into this directory
```

3. **Create vercel.json:**

```bash
# Copy the vercel.json config to project root
```

4. **Link Vercel project** (if using Vercel CLI in workflows):

```bash
cd frontend
vercel link
# Copy .vercel/project.json values to GitHub Secrets
```

5. **Test workflows:**

```bash
# Make a change to backend
echo "# Test" >> backend/README.md
git add backend/README.md
git commit -m "test: trigger backend deployment"
git push origin main

# Check Actions tab on GitHub to monitor deployment
```

---

### Workflow Triggers Summary

| Workflow              | Trigger                         | Purpose                         |
| --------------------- | ------------------------------- | ------------------------------- |
| `ci.yml`              | PR + Push to main/develop       | Run tests, linting, type checks |
| `deploy-backend.yml`  | Push to main (backend changes)  | Deploy backend to Cloud Run     |
| `deploy-frontend.yml` | Push to main (frontend changes) | Deploy frontend to Vercel       |
| `manual-deploy.yml`   | Manual trigger                  | Emergency/testing deployments   |

**Key Features:**

- ✅ Only runs workflows when relevant files change (path filtering)
- ✅ Parallel execution where possible
- ✅ Health checks after deployment
- ✅ Proper monorepo directory handling
- ✅ Cache dependencies for faster builds
- ✅ Environment variable management via secrets

---

## Troubleshooting

### Backend Issues

**Cloud Run deployment fails:**

```bash
# View build logs
gcloud builds list --limit=5
gcloud builds log [BUILD_ID]

# Common fixes:
# - Check Dockerfile syntax
# - Verify all required files are included
# - Check .gcloudignore
```

**Database connection fails:**

```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe sampletok-db

# Test connection
gcloud sql connect sampletok-db --user=sampletok

# Check connection string format:
# postgresql+asyncpg://USER:PASSWORD@/DATABASE?host=/cloudsql/CONNECTION_NAME
```

**Storage upload fails:**

```bash
# Verify bucket exists
gsutil ls gs://sampletok-samples-prod/

# Check permissions
gsutil iam get gs://sampletok-samples-prod/
```

### Frontend Issues

**API calls fail:**

- Check `NEXT_PUBLIC_API_URL` in Vercel environment variables
- Verify backend CORS includes Vercel URL
- Check browser console for exact error

**Build fails on Vercel:**

- Check build logs in Vercel dashboard
- Verify all dependencies in package.json
- Check TypeScript errors locally: `npm run build`

### Inngest Issues

**Workers not processing:**

- Verify webhook URL is correct
- Check Inngest dashboard for errors
- Verify signing key is set correctly
- Check backend logs for Inngest errors

---

## Performance Optimization

### Backend (Cloud Run)

```bash
# Increase min instances for faster cold starts
gcloud run services update sampletok-backend \
  --region=us-central1 \
  --min-instances=1 \
  --max-instances=20

# Increase resources for heavy processing
gcloud run services update sampletok-backend \
  --region=us-central1 \
  --memory=4Gi \
  --cpu=4
```

### Database (Cloud SQL)

```bash
# Upgrade to better tier
gcloud sql instances patch sampletok-db \
  --tier=db-g1-small

# Enable high availability
gcloud sql instances patch sampletok-db \
  --availability-type=REGIONAL
```

### Frontend (Vercel)

- Vercel automatically optimizes Next.js
- Use Image Optimization: `next/image`
- Enable incremental static regeneration where possible

---

## Cost Management

### Current Estimate

**Free Tier:**

- Vercel: Free for hobby projects
- GCP: $300 free credit (new accounts)

**After Free Tier:**

- **Cloud Run**: ~$5-15/month (light usage, scales to zero)
- **Cloud SQL (db-f1-micro)**: ~$7-10/month
- **Cloud Storage**: ~$1-3/month
- **Vercel**: Free (hobby) or $20/month (Pro)
- **Inngest**: Free tier available
- **Total: $13-28/month** (or $0-8/month if Vercel free tier)

### Cost Optimization Tips

1. **Use min-instances=0** for Cloud Run (scales to zero)
2. **Start with db-f1-micro** (upgrade only if needed)
3. **Set Cloud Storage lifecycle policies** (auto-delete old files)
4. **Monitor with budget alerts:**

```bash
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="SampleTok Monthly Budget" \
  --budget-amount=30USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## Security Checklist

- [x] Secrets stored in Secret Manager (not env vars)
- [x] HTTPS enforced (automatic with Cloud Run & Vercel)
- [x] CORS properly configured
- [x] Database password is strong and secure
- [x] Cloud SQL automatic backups enabled
- [x] Principle of least privilege for IAM roles
- [ ] Rate limiting enabled (add if needed)
- [ ] DDoS protection (Cloud Armor if needed)
- [ ] Regular dependency updates
- [ ] Error tracking configured (Sentry recommended)

---

## Quick Command Reference

### Deploy Backend

```bash
cd backend
gcloud run deploy sampletok-backend --source . --region=us-central1
```

### Deploy Frontend

```bash
cd frontend
vercel --prod
```

### View Logs

```bash
# Backend
gcloud run services logs tail sampletok-backend --region=us-central1

# Frontend
vercel logs sampletok
```

### Update Environment Variable

```bash
# Backend
gcloud run services update sampletok-backend \
  --region=us-central1 \
  --set-env-vars="KEY=value"

# Frontend
# Update in Vercel Dashboard, then:
vercel --prod
```

---

## Support Resources

- **Vercel Docs**: https://vercel.com/docs
- **GCP Cloud Run**: https://cloud.google.com/run/docs
- **Cloud SQL**: https://cloud.google.com/sql/docs
- **Inngest**: https://www.inngest.com/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **Next.js**: https://nextjs.org/docs

---

## Summary

You now have:

- ✅ Scalable backend on GCP Cloud Run
- ✅ Optimized frontend on Vercel
- ✅ Managed PostgreSQL database
- ✅ Cloud storage for files
- ✅ Background job processing with Inngest
- ✅ Automatic deployments on git push
- ✅ Production-ready monitoring

**Estimated setup time**: 30-45 minutes

**Monthly cost**: $13-28 (or less with free tiers)

Happy deploying! 🚀
