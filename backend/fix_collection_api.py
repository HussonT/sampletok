#!/usr/bin/env python3
"""
Simple script to reset a stuck collection via the deployed admin API endpoint.
No database connection needed - uses the HTTP API.
"""
import requests
import json

# Configuration
API_URL = "https://sampletok-backend-mro5z6ayaq-uc.a.run.app"
ADMIN_KEY = "-b7PKy4GP1ZiXY4itRmSZOh_gVExVPesNomAUI3NAe0"
COLLECTION_ID = "2a3960d1-f762-4947-8f50-f2a736dd1bf6"

def reset_collection():
    """Reset a collection and refund credits via admin API"""

    print(f"Resetting collection {COLLECTION_ID}...\n")

    # Call the new collection-by-id endpoint (if deployed)
    url = f"{API_URL}/api/v1/admin/reset-collection/{COLLECTION_ID}"
    headers = {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json"
    }

    print(f"Calling: POST {url}")
    print(f"Headers: X-Admin-Key: {ADMIN_KEY[:10]}...")
    print()

    try:
        response = requests.post(url, headers=headers, timeout=30)

        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS!")
            print(f"   Collection '{data.get('collection_name')}' reset from '{data.get('old_status')}' to 'pending'")
            print(f"   Credits refunded: {data.get('credits_refunded')}")
            print(f"   New balance: {data.get('new_balance')}")
        elif response.status_code == 404:
            print("\n❌ Endpoint not found - the new endpoint might not be deployed yet")
            print("   Please deploy the latest changes or re-authenticate gcloud")
        else:
            print(f"\n❌ Error: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return False

    return response.status_code == 200

if __name__ == "__main__":
    try:
        success = reset_collection()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
