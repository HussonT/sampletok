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
  --allow-unauthenticated

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
