#!/usr/bin/env python3
"""
Script to retrigger failed or stuck stem separation jobs.
This will resend the Inngest event for all pending or failed stems.
"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict
from sqlalchemy import select

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import Stem, StemProcessingStatus
from app.inngest_functions import inngest_client
import inngest


async def retrigger_failed_stems():
    """Find failed/pending stems and retrigger their Inngest jobs"""

    async with AsyncSessionLocal() as db:
        # Get stems that are stuck (pending, uploading, processing) or failed
        result = await db.execute(
            select(Stem).where(
                Stem.status.in_([
                    StemProcessingStatus.PENDING,
                    StemProcessingStatus.UPLOADING,
                    StemProcessingStatus.PROCESSING,
                    StemProcessingStatus.FAILED
                ])
            )
        )
        stems = result.scalars().all()

        if not stems:
            print("✅ No stems need retriggering")
            return

        # Group stems by sample_id
        stems_by_sample = defaultdict(list)
        for stem in stems:
            stems_by_sample[str(stem.parent_sample_id)].append(stem)

        print(f"Found {len(stems)} stems across {len(stems_by_sample)} samples to retrigger\n")

        # Retrigger each sample's stems
        for sample_id, sample_stems in stems_by_sample.items():
            stem_ids = [str(stem.id) for stem in sample_stems]
            stem_types = [stem.stem_type.value for stem in sample_stems]

            print(f"Sample {sample_id}:")
            print(f"  Stems: {', '.join(stem_types)}")
            print(f"  Stem IDs: {stem_ids}")

            try:
                # Send Inngest event
                await inngest_client.send(
                    inngest.Event(
                        name="stem/separation.submitted",
                        data={
                            "sample_id": sample_id,
                            "stem_ids": stem_ids
                        }
                    )
                )
                print(f"  ✅ Successfully triggered Inngest job\n")

            except Exception as e:
                print(f"  ❌ Failed to trigger: {e}\n")

        print(f"✅ Completed! Retriggered {len(stems_by_sample)} jobs")


if __name__ == "__main__":
    print("=== Retrigger Failed Stems ===\n")
    asyncio.run(retrigger_failed_stems())
