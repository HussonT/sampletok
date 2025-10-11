#!/usr/bin/env python
"""
Serve Inngest functions for local development
"""

import inngest
import inngest.fast_api
from fastapi import FastAPI
import uvicorn
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from app.inngest_functions import get_all_functions, inngest_client

# Create FastAPI app for serving Inngest functions
app = FastAPI(title="Inngest Functions Server")

# Serve the Inngest functions
inngest.fast_api.serve(
    app,
    inngest_client,
    get_all_functions()
)

if __name__ == "__main__":
    print("Starting Inngest functions server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")