#!/usr/bin/env python3
"""Check detailed info for samples"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://sampletok:sampletok@localhost:5432/sampletok"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT id, tiktok_url, tiktok_id, creator_username, description, status
        FROM samples
        WHERE status = 'COMPLETED'
        ORDER BY created_at DESC
    """))

    print("Completed samples:")
    for row in result:
        print(f"\nID: {row[0]}")
        print(f"URL: {row[1]}")
        print(f"TikTok ID: {row[2]}")
        print(f"Creator: {row[3]}")
        print(f"Title: {row[4]}")
        print(f"Status: {row[5]}")