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
echo "To deploy to Cloud Run, use:"
echo "  gcloud run deploy sampletok-backend \\"
echo "    --image ${IMAGE_PATH} \\"
echo "    --platform managed \\"
echo "    --region ${REGION} \\"
echo "    --project ${PROJECT_ID}"
echo ""
