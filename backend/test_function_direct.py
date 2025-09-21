#!/usr/bin/env python
"""Test the Inngest function directly to see what's failing"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.inngest_functions import process_tiktok_video

# Mock context and step
class MockContext:
    def __init__(self, data):
        self.event = MockEvent(data)

class MockEvent:
    def __init__(self, data):
        self.data = data

class MockStep:
    def run(self, step_id, func, *args):
        print(f"Running step: {step_id}")
        try:
            result = func(*args)
            print(f"Step {step_id} completed: {result}")
            return result
        except Exception as e:
            print(f"Step {step_id} failed: {e}")
            import traceback
            traceback.print_exc()
            raise

# Test data
test_data = {
    "sample_id": "4987740e-9001-4ae5-bf90-550a45556398",
    "url": "https://www.tiktok.com/@test/video/123"
}

ctx = MockContext(test_data)
step = MockStep()

print("Testing process_tiktok_video function...")
try:
    result = process_tiktok_video(ctx, step)
    print(f"Success: {result}")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()