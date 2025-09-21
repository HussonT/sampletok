#!/usr/bin/env python
"""
Serve simple Inngest function for debugging
"""

import inngest
import inngest.fast_api
from fastapi import FastAPI, Request, Response
import uvicorn
import logging
import sys

# Configure comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from app.inngest_simple import get_simple_functions, inngest_client

# Create FastAPI app
app = FastAPI(title="Simple Inngest Test Server")

# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n{'='*50}")
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")

    # Read body if it's a POST request
    if request.method == "POST":
        body = await request.body()
        print(f"Body: {body.decode('utf-8') if body else 'No body'}")
        # Create new request with the body we read
        request = Request(request.scope, receive=lambda: {"type": "http.request", "body": body})

    try:
        response = await call_next(request)
        print(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        return Response(content=str(e), status_code=500)

# Serve the Inngest functions
inngest.fast_api.serve(
    app,
    inngest_client,
    get_simple_functions()
)

if __name__ == "__main__":
    print("Starting SIMPLE Inngest test server on http://localhost:8002")
    print("Functions registered:", get_simple_functions())
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="debug")