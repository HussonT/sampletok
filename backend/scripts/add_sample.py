from app.core.database import AsyncSessionLocal
from app.models import Sample, ProcessingStatus
from datetime import datetime
import uuid
import asyncio

async def add_sample():
    async with AsyncSessionLocal() as db:
        # Add a sample with a real audio URL (free music)
        sample = Sample(
            id=uuid.uuid4(),
            tiktok_url='https://www.tiktok.com/@test/video/123',
            tiktok_id='123456789',
            title='Test Sample',
            creator_username='testuser',
            creator_name='Test User',
            description='This is a test sample with real audio',
            view_count=1000,
            like_count=100,
            comment_count=10,
            share_count=5,
            duration_seconds=30,
            audio_url_mp3='https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
            status=ProcessingStatus.COMPLETED,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(sample)
        await db.commit()
        print('Sample added successfully!')

asyncio.run(add_sample())