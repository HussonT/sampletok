#!/bin/bash

# Sampletok Backend - Build and Deploy Script
# This script builds the Docker image and pushes it to Google Artifact Registry

set -e  # Exit on error

# Configuration
PROJECT_ID="sampletok"
REGION="us-central1"
REPOSITORY="sampletok-backend"
IMAGE_NAME="sampletok-backend"
IMAGE_TAG="${1:-latest}"  # Use first argument as tag, default to 'latest'

# Full image path
IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "============================================="
echo "Sampletok Backend Deployment"
echo "============================================="
echo "Project:    ${PROJECT_ID}"
echo "Region:     ${REGION}"
echo "Repository: ${REPOSITORY}"
echo "Image:      ${IMAGE_NAME}"
echo "Tag:        ${IMAGE_TAG}"
echo "Full path:  ${IMAGE_PATH}"
echo "============================================="
echo ""

# Ensure we're in the backend directory
cd "$(dirname "$0")"

echo "Building and pushing image to Artifact Registry..."
echo ""

# Build and push using Cloud Build
gcloud builds submit \
  --tag "${IMAGE_PATH}" \
  --project="${PROJECT_ID}" \
  .

echo ""
echo "============================================="
echo "Build complete!"
echo "============================================="
echo ""
echo "Image available at:"
echo "  ${IMAGE_PATH}"
echo ""

# Deploy to Cloud Run
SERVICE_NAME="sampletok-backend"
echo "Deploying to Cloud Run..."
echo ""

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_PATH}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --set-env-vars="ENVIRONMENT=production,STORAGE_TYPE=r2,S3_BUCKET_NAME=sampletok-samples,AWS_REGION=auto,API_V1_STR=/api/v1,DEBUG=False,DATABASE_ECHO=False" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,SECRET_KEY=SECRET_KEY:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,RAPIDAPI_KEY=RAPIDAPI_KEY:latest,RAPIDAPI_INSTAGRAM_KEY=RAPIDAPI_INSTAGRAM_KEY:latest,RAPIDAPI_INSTAGRAM_HOST=RAPIDAPI_INSTAGRAM_HOST:latest,INNGEST_EVENT_KEY=INNGEST_EVENT_KEY:latest,INNGEST_SIGNING_KEY=INNGEST_SIGNING_KEY:latest,AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID:latest,AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY:latest,S3_ENDPOINT_URL=S3_ENDPOINT_URL:latest,R2_PUBLIC_DOMAIN=R2_PUBLIC_DOMAIN:latest,BACKEND_CORS_ORIGINS=BACKEND_CORS_ORIGINS:latest,CLERK_FRONTEND_API=CLERK_FRONTEND_API:latest,CLERK_SECRET_KEY=CLERK_SECRET_KEY:latest,ADMIN_API_KEY=ADMIN_API_KEY:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,STRIPE_PRICE_BASIC_MONTHLY=STRIPE_PRICE_BASIC_MONTHLY:latest,STRIPE_PRICE_BASIC_ANNUAL=STRIPE_PRICE_BASIC_ANNUAL:latest,STRIPE_PRICE_PRO_MONTHLY=STRIPE_PRICE_PRO_MONTHLY:latest,STRIPE_PRICE_PRO_ANNUAL=STRIPE_PRICE_PRO_ANNUAL:latest,STRIPE_PRICE_ULTIMATE_MONTHLY=STRIPE_PRICE_ULTIMATE_MONTHLY:latest,STRIPE_PRICE_ULTIMATE_ANNUAL=STRIPE_PRICE_ULTIMATE_ANNUAL:latest,STRIPE_PRICE_TOPUP_SMALL=STRIPE_PRICE_TOPUP_SMALL:latest,STRIPE_PRICE_TOPUP_MEDIUM=STRIPE_PRICE_TOPUP_MEDIUM:latest,STRIPE_PRICE_TOPUP_LARGE=STRIPE_PRICE_TOPUP_LARGE:latest,LALAL_API_KEY=LALAL_API_KEY:latest,FRONTEND_URL=FRONTEND_URL:latest"

echo ""
echo "============================================="
echo "Deployment complete!"
echo "============================================="
echo ""
echo "Service URL:"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format="value(status.url)")
echo "${SERVICE_URL}"
echo ""

# Sync Inngest functions
echo "============================================="
echo "Syncing Inngest functions..."
echo "============================================="
echo ""
SYNC_RESPONSE=$(curl -s -X PUT "${SERVICE_URL}/api/inngest")
echo "Sync response: ${SYNC_RESPONSE}"

# Check if sync was successful
if echo "${SYNC_RESPONSE}" | grep -q '"ok": true'; then
  echo "✅ Inngest functions synced successfully!"
else
  echo "⚠️  Warning: Inngest sync may have failed. Please check manually."
  echo "   You can manually sync by running:"
  echo "   curl -X PUT ${SERVICE_URL}/api/inngest"
fi
echo ""
