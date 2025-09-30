#!/usr/bin/env python3
"""Check database for sample status"""

import asyncio
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = "postgresql://sampletok:sampletok@localhost:5432/sampletok"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT id, status, audio_url_mp3, waveform_url, error_message, created_at, updated_at
        FROM samples
        ORDER BY created_at DESC
        LIMIT 5
    """))

    print("Recent samples:")
    for row in result:
        print(f"\nID: {row[0]}")
        print(f"Status: {row[1]}")
        print(f"Audio URL: {row[2]}")
        print(f"Waveform URL: {row[3]}")
        print(f"Error: {row[4]}")
        print(f"Created: {row[5]}")
        print(f"Updated: {row[6]}")
        print("-" * 50)