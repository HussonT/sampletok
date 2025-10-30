#!/bin/bash
# Reset stuck collection in production

COLLECTION_ID="2a3960d1-f762-4947-8f50-f2a736dd1bf6"

echo "Connecting to production database via Cloud SQL Proxy..."

# Get the DATABASE_URL from secrets
DATABASE_URL=$(gcloud secrets versions access latest --secret="DATABASE_URL" --project=sampletok 2>/dev/null)

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Could not retrieve DATABASE_URL from secrets"
    exit 1
fi

# Export it for the script
export DATABASE_URL

# Run the Python script
python reset_collection.py

