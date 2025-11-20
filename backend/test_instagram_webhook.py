#!/usr/bin/env python3
"""
Test script for Instagram webhook endpoint.

This script simulates Meta's webhook verification and event delivery.
"""
import asyncio
import hmac
import hashlib
import json
from typing import Dict, Any


def generate_signature(payload: bytes, secret: str) -> str:
    """Generate X-Hub-Signature-256 header value"""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


async def test_webhook_verification():
    """Test GET request for webhook verification"""
    print("\n" + "="*60)
    print("TEST 1: Webhook Verification (GET)")
    print("="*60)

    # Simulate Meta's webhook verification request
    verify_token = "my_verify_token_123"
    challenge = "1234567890"
    mode = "subscribe"

    print(f"\nSimulating GET request:")
    print(f"  hub.mode = {mode}")
    print(f"  hub.verify_token = {verify_token}")
    print(f"  hub.challenge = {challenge}")

    # Import the service
    import sys
    sys.path.insert(0, '/Users/tomhusson/sideprojects/sampletok/backend')
    from app.services.instagram.graph_api_service import InstagramGraphAPIService

    service = InstagramGraphAPIService()
    result = await service.verify_webhook(verify_token, challenge)

    if result == challenge:
        print(f"\n✓ Verification successful! Challenge returned: {result}")
    else:
        print(f"\n✗ Verification failed! Expected {challenge}, got {result}")

    # Test with wrong token
    print(f"\nTesting with wrong token:")
    result = await service.verify_webhook("wrong_token", challenge)
    if result is None:
        print(f"✓ Correctly rejected wrong token")
    else:
        print(f"✗ Should have rejected wrong token!")


async def test_webhook_event():
    """Test POST request for webhook event"""
    print("\n" + "="*60)
    print("TEST 2: Webhook Event Processing (POST)")
    print("="*60)

    # Sample Instagram webhook payload
    event_data = {
        "object": "instagram",
        "entry": [
            {
                "id": "instagram_business_account_id",
                "time": 1234567890,
                "changes": [
                    {
                        "field": "mentions",
                        "value": {
                            "media_id": "123456789",
                            "comment_id": "987654321"
                        }
                    }
                ]
            }
        ]
    }

    payload = json.dumps(event_data).encode('utf-8')
    app_secret = "test_app_secret_456"

    # Generate signature
    signature = generate_signature(payload, app_secret)

    print(f"\nSimulating POST request:")
    print(f"  Payload size: {len(payload)} bytes")
    print(f"  X-Hub-Signature-256: {signature}")
    print(f"  Event object: {event_data['object']}")
    print(f"  Event field: {event_data['entry'][0]['changes'][0]['field']}")

    # Verify signature computation
    expected_sig = "sha256=" + hmac.new(
        app_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    if signature == expected_sig:
        print(f"\n✓ Signature generation correct")
    else:
        print(f"\n✗ Signature mismatch!")

    # Import the service
    import sys
    sys.path.insert(0, '/Users/tomhusson/sideprojects/sampletok/backend')
    from app.services.instagram.graph_api_service import InstagramGraphAPIService

    service = InstagramGraphAPIService()

    print(f"\nProcessing webhook event...")
    try:
        await service.process_webhook_event(event_data)
        print(f"✓ Event processed successfully (logged)")
    except Exception as e:
        print(f"✗ Error processing event: {e}")


async def test_signature_verification():
    """Test signature verification logic"""
    print("\n" + "="*60)
    print("TEST 3: Signature Verification")
    print("="*60)

    payload = b'{"test": "data"}'
    secret = "my_secret_key"

    # Generate valid signature
    valid_sig = generate_signature(payload, secret)
    print(f"\nValid signature: {valid_sig}")

    # Test constant-time comparison
    print(f"\nTesting signature comparison:")

    # Same signature - should match
    result1 = hmac.compare_digest(valid_sig, valid_sig)
    print(f"  Same signature: {result1} {'✓' if result1 else '✗'}")

    # Different signature - should not match
    wrong_sig = generate_signature(payload, "wrong_secret")
    result2 = hmac.compare_digest(valid_sig, wrong_sig)
    print(f"  Wrong signature: {result2} {'✓ (correctly rejected)' if not result2 else '✗'}")

    # Tampered payload - should not match
    tampered_payload = b'{"test": "tampered"}'
    tampered_sig = generate_signature(tampered_payload, secret)
    result3 = hmac.compare_digest(valid_sig, tampered_sig)
    print(f"  Tampered payload: {result3} {'✓ (correctly rejected)' if not result3 else '✗'}")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Instagram Webhook Endpoint Test Suite")
    print("="*60)

    await test_webhook_verification()
    await test_webhook_event()
    await test_signature_verification()

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
