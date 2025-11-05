# Implementation Prompt: V1 Tagging & Search System (REVISED)

## Overview

Implement a tagging and search system for SampleTok with **incremental delivery over 3-4 days**. This follows Phase 1 + 2 from `TAGGING_SEARCH_APPROACHES.md` - PostgreSQL with enhanced filtering and full-text search.

**Key Changes from Original Plan:**
- ⚠️ **No facets in V1** - Adds 500ms+ per request, defer to Elasticsearch phase
- ⚠️ **No Zustand store** - Use React state + TanStack Query
- ⚠️ **Fixed tsvector backfill** - Trigger-based approach that works with existing data
- ⚠️ **Fixed tag filtering** - OR logic (&&) not AND logic (@>)
- ⚠️ **Added error handling** - Timeouts, validation, graceful degradation

## Reference UI (Splice-style Layout)

The target UI includes:
- **Top search bar** with real-time search
- **Tag pills** showing popular tags (clickable to filter)
- **Filter bar** with dropdowns: Key, BPM, Sort
- **Active filters display** as pills with X buttons to clear
- **Results table** with waveform, BPM, Key columns
- **Results count** display

## Incremental Implementation Roadmap

### Phase 1: Search Only (Day 1)
**Goal:** Text search with relevance ranking

- [ ] Database migration (tsvector with trigger)
- [ ] Backfill script (run separately)
- [ ] Search endpoint (basic, no filters yet)
- [ ] Frontend search bar
- [ ] Test search works on existing data

**Deliverable:** Users can search samples by text

### Phase 2: Basic Filters (Day 2)
**Goal:** BPM and Key filtering

- [ ] Add BPM range filter to backend
- [ ] Add Key filter to backend
- [ ] Frontend filter dropdowns (hard-coded options)
- [ ] Display active filters

**Deliverable:** Users can filter by BPM and Key

### Phase 3: Tag Filtering (Day 3)
**Goal:** Tag-based discovery

- [ ] Fix tag filtering logic (OR operator)
- [ ] Add popular tags endpoint
- [ ] Frontend tag pills component
- [ ] Test tag filtering

**Deliverable:** Users can filter by tags

### Phase 4: Polish & Production (Day 4)
**Goal:** Production-ready

- [ ] Add timeouts to all queries
- [ ] Add input validation
- [ ] Add performance logging
- [ ] Error handling
- [ ] Load test with 10k samples

**Deliverable:** System is production-ready

---

## Phase 1: Search Only (Day 1)

### Step 1.1: Database Migration (Schema Only)

**Location**: Create new migration in `backend/alembic/versions/`

**IMPORTANT:** This migration only handles schema changes. Backfill is done separately.

```python
"""Add full-text search with tsvector

Revision ID: [auto-generated]
Revises: [previous_revision]
Create Date: [auto-generated]
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

def upgrade():
    # Add tsvector column (nullable, will be backfilled separately)
    op.add_column('samples', sa.Column('search_vector', TSVECTOR, nullable=True))

    # Create update function
    op.execute('''
        CREATE FUNCTION update_search_vector() RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('english', coalesce(NEW.tiktok_title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(NEW.creator_username, '')), 'C') ||
            setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'D');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Create trigger for future inserts/updates
    op.execute('''
        CREATE TRIGGER samples_search_vector_update
          BEFORE INSERT OR UPDATE ON samples
          FOR EACH ROW
          EXECUTE FUNCTION update_search_vector();
    ''')

def downgrade():
    op.execute('DROP TRIGGER IF EXISTS samples_search_vector_update ON samples')
    op.execute('DROP FUNCTION IF EXISTS update_search_vector()')
    op.drop_column('samples', 'search_vector')
```

**Run the migration:**
```bash
cd backend
alembic upgrade head
```

### Step 1.2: Backfill Script (Run Separately)

**Location**: `backend/scripts/backfill_search_vectors.py`

Create a separate script to backfill existing samples:

```python
"""
Backfill search_vector for existing samples

Run this AFTER the migration:
    python scripts/backfill_search_vectors.py

This script:
1. Updates search_vector for all samples without it
2. Creates the GIN index after backfill (much faster)
"""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = os.getenv("DATABASE_URL")

async def backfill_search_vectors():
    engine = create_async_engine(DATABASE_URL)

    async with AsyncSession(engine) as session:
        # Count samples that need backfill
        count_query = text("SELECT COUNT(*) FROM samples WHERE search_vector IS NULL")
        result = await session.execute(count_query)
        total = result.scalar()

        print(f"Found {total} samples to backfill...")

        if total == 0:
            print("No samples to backfill. Checking if index exists...")

            # Check if index exists
            index_check = text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'ix_samples_search_vector'
                )
            """)
            index_exists = await session.scalar(index_check)

            if not index_exists:
                print("Creating GIN index...")
                await session.execute(text(
                    "CREATE INDEX ix_samples_search_vector ON samples USING GIN (search_vector)"
                ))
                await session.commit()
                print("✅ Index created!")
            else:
                print("✅ Index already exists!")

            return

        # Backfill search_vector
        print("Backfilling search_vector...")
        backfill_query = text("""
            UPDATE samples
            SET search_vector =
              setweight(to_tsvector('english', coalesce(tiktok_title, '')), 'A') ||
              setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
              setweight(to_tsvector('english', coalesce(creator_username, '')), 'C') ||
              setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'D')
            WHERE search_vector IS NULL
        """)

        await session.execute(backfill_query)
        await session.commit()

        print(f"✅ Backfilled {total} samples!")

        # Create GIN index AFTER backfill (much faster this way)
        print("Creating GIN index...")
        await session.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_samples_search_vector ON samples USING GIN (search_vector)"
        ))
        await session.commit()

        print("✅ Index created!")
        print("✅ Backfill complete!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(backfill_search_vectors())
```

**Run the backfill:**
```bash
cd backend
python scripts/backfill_search_vectors.py
```

**Verify it worked:**
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM samples WHERE search_vector IS NOT NULL;"
# Should return: same count as total samples

psql $DATABASE_URL -c "\d samples"
# Should show: search_vector column and ix_samples_search_vector index
```

### Step 1.3: Update Sample Model

**Location**: `backend/app/models/sample.py`

```python
from sqlalchemy.dialects.postgresql import TSVECTOR

class Sample(Base):
    # ... existing fields ...

    # Full-text search vector (managed by trigger)
    search_vector = Column(TSVECTOR, nullable=True)
```

### Step 1.4: Create Simple Search Schema

**Location**: `backend/app/schemas/sample.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class SampleSearchParams(BaseModel):
    """V1 Search parameters (simplified - no facets)"""
    # Text search
    search: Optional[str] = Field(None, max_length=200, description="Full-text search query")

    # Sorting
    sort_by: str = Field(
        "created_at_desc",
        description="Sort order: created_at_desc, created_at_asc, views_desc"
    )

    # Pagination
    skip: int = Field(0, ge=0, le=10000)
    limit: int = Field(20, ge=1, le=100)


class SampleSearchResponse(BaseModel):
    """V1 Search results (NO FACETS - defer to Elasticsearch phase)"""
    samples: list[SampleResponse]
    total: int
    skip: int
    limit: int
```

### Step 1.5: Implement Search Endpoint (V1)

**Location**: `backend/app/api/v1/endpoints/samples.py`

```python
import asyncio
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

logger = logging.getLogger(__name__)

@router.get("/", response_model=SampleSearchResponse)
async def search_samples(
    params: SampleSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    V1 Search endpoint - Text search only, no filters

    - Full-text search with relevance ranking
    - Sorted by relevance (if search) or created_at
    - No facets (defer to Elasticsearch phase)
    """

    start_time = time.time()

    # Base query - only completed samples
    query = select(Sample).where(Sample.status == "completed")

    # Full-text search with PostgreSQL tsvector
    if params.search:
        # Convert search query to tsquery
        ts_query = func.plainto_tsquery('english', params.search)

        # Filter by tsvector match
        query = query.where(Sample.search_vector.op('@@')(ts_query))

        # Sort by relevance
        query = query.order_by(
            func.ts_rank(Sample.search_vector, ts_query).desc()
        )
    else:
        # Default sort
        if params.sort_by == "created_at_desc":
            query = query.order_by(Sample.created_at.desc())
        elif params.sort_by == "created_at_asc":
            query = query.order_by(Sample.created_at.asc())
        elif params.sort_by == "views_desc":
            query = query.order_by(Sample.view_count.desc())

    # Get total count
    count_query = select(func.count()).select_from(
        select(Sample)
        .where(Sample.status == "completed")
        .subquery()
    )
    if params.search:
        ts_query = func.plainto_tsquery('english', params.search)
        count_query = count_query.where(Sample.search_vector.op('@@')(ts_query))

    try:
        # Execute with timeout
        total = await asyncio.wait_for(
            db.scalar(count_query),
            timeout=5.0
        )
        total = total or 0
    except asyncio.TimeoutError:
        logger.error("Count query timeout")
        raise HTTPException(
            status_code=504,
            detail="Search timeout. Try a simpler query."
        )

    # Pagination
    query = query.offset(params.skip).limit(params.limit)

    # Execute main query with timeout
    try:
        result = await asyncio.wait_for(
            db.execute(query),
            timeout=5.0
        )
        samples = result.scalars().all()
    except asyncio.TimeoutError:
        logger.error("Search query timeout")
        raise HTTPException(
            status_code=504,
            detail="Search timeout. Try a simpler query."
        )

    # Log slow queries
    query_time = time.time() - start_time
    if query_time > 1.0:
        logger.warning(
            f"Slow search query: {query_time:.2f}s",
            extra={"search": params.search, "duration": query_time}
        )

    return SampleSearchResponse(
        samples=samples,
        total=total,
        skip=params.skip,
        limit=params.limit
    )
```

### Step 1.6: Frontend Search Bar (Simple)

**Location**: `frontend/app/components/features/search-bar.tsx`

```typescript
'use client';

import { Search, X } from 'lucide-react';
import { Input } from '@/app/components/ui/input';
import { useState } from 'react';
import { useDebouncedCallback } from 'use-debounce';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  const [localSearch, setLocalSearch] = useState(value);

  // Debounce search input
  const debouncedSearch = useDebouncedCallback((value: string) => {
    onChange(value);
  }, 300);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setLocalSearch(newValue);
    debouncedSearch(newValue);
  };

  const handleClear = () => {
    setLocalSearch('');
    onChange('');
  };

  return (
    <div className="relative w-full max-w-2xl">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Search samples by description, creator, tags..."
        value={localSearch}
        onChange={handleChange}
        className="pl-10 pr-10"
      />
      {localSearch && (
        <button
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
```

### Step 1.7: Update Samples Page (Simple State)

**Location**: `frontend/app/components/features/samples-table.tsx`

**NO ZUSTAND** - Just use React state + TanStack Query

```typescript
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/app/lib/api/client';
import { SearchBar } from './search-bar';

export function SamplesTable() {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('created_at_desc');

  // Fetch samples with TanStack Query
  const { data, isLoading } = useQuery({
    queryKey: ['samples', 'search', search, sortBy],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      params.set('sort_by', sortBy);
      params.set('limit', '20');

      const response = await apiClient.get(`/samples?${params.toString()}`);
      return response.data;
    },
    staleTime: 30000, // Cache for 30 seconds
  });

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <SearchBar value={search} onChange={setSearch} />

      {/* Results Count */}
      {data && (
        <div className="text-sm text-muted-foreground">
          {data.total.toLocaleString()} results
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <div className="space-y-2">
          {data?.samples.map(sample => (
            <SampleRow key={sample.id} sample={sample} />
          ))}
        </div>
      )}
    </div>
  );
}
```

**✅ Phase 1 Complete: Text search works!**

---

## Phase 2: Basic Filters (Day 2)

### Step 2.1: Add Filter Indexes

**Location**: Create new migration

```python
"""Add filtering indexes

Revision ID: [auto-generated]
"""

def upgrade():
    op.create_index('ix_samples_bpm', 'samples', ['bpm'])
    op.create_index('ix_samples_key', 'samples', ['key'])

    # GIN index for JSONB tag queries
    op.execute('CREATE INDEX ix_samples_tags_gin ON samples USING GIN (tags)')

def downgrade():
    op.execute('DROP INDEX IF EXISTS ix_samples_tags_gin')
    op.drop_index('ix_samples_key', table_name='samples')
    op.drop_index('ix_samples_bpm', table_name='samples')
```

### Step 2.2: Update Search Schema

**Location**: `backend/app/schemas/sample.py`

```python
class SampleSearchParams(BaseModel):
    """V2 Search parameters - add BPM and Key filters"""
    search: Optional[str] = Field(None, max_length=200)

    # NEW: BPM filtering
    bpm_min: Optional[int] = Field(None, ge=0, le=300)
    bpm_max: Optional[int] = Field(None, ge=0, le=300)

    # NEW: Key filtering
    key: Optional[str] = Field(None, description="Musical key (e.g., 'C Major')")

    sort_by: str = Field("created_at_desc")
    skip: int = Field(0, ge=0, le=10000)
    limit: int = Field(20, ge=1, le=100)
```

### Step 2.3: Update Search Endpoint

**Location**: `backend/app/api/v1/endpoints/samples.py`

Add filtering to existing search endpoint:

```python
@router.get("/", response_model=SampleSearchResponse)
async def search_samples(
    params: SampleSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # ... existing search logic ...

    # NEW: BPM range filter
    if params.bpm_min is not None:
        query = query.where(Sample.bpm >= params.bpm_min)
    if params.bpm_max is not None:
        query = query.where(Sample.bpm <= params.bpm_max)

    # NEW: Key filter
    if params.key:
        query = query.where(Sample.key == params.key)

    # ... rest of existing code ...
```

### Step 2.4: Add Filter Bar Component

**Location**: `frontend/app/components/features/filter-bar.tsx`

```typescript
'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select';
import { Button } from '@/app/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/ui/popover';
import { SlidersHorizontal } from 'lucide-react';

// Hard-coded options (no need to fetch from backend)
const MUSICAL_KEYS = [
  'C Major', 'C Minor', 'C# Major', 'C# Minor',
  'D Major', 'D Minor', 'D# Major', 'D# Minor',
  'E Major', 'E Minor', 'F Major', 'F Minor',
  'F# Major', 'F# Minor', 'G Major', 'G Minor',
  'G# Major', 'G# Minor', 'A Major', 'A Minor',
  'A# Major', 'A# Minor', 'B Major', 'B Minor',
];

const BPM_RANGES = [
  { label: '60-90 (Slow)', min: 60, max: 90 },
  { label: '90-120 (Medium)', min: 90, max: 120 },
  { label: '120-140 (Upbeat)', min: 120, max: 140 },
  { label: '140-180 (Fast)', min: 140, max: 180 },
];

interface FilterBarProps {
  bpmMin: number | null;
  bpmMax: number | null;
  musicalKey: string | null;
  sortBy: string;
  onBpmChange: (min: number | null, max: number | null) => void;
  onKeyChange: (key: string | null) => void;
  onSortChange: (sort: string) => void;
}

export function FilterBar({
  bpmMin,
  bpmMax,
  musicalKey,
  sortBy,
  onBpmChange,
  onKeyChange,
  onSortChange,
}: FilterBarProps) {
  return (
    <div className="flex items-center gap-3 py-3 border-y">
      {/* Key Filter */}
      <Select value={musicalKey || '__all__'} onValueChange={(v) => onKeyChange(v === '__all__' ? null : v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="Key" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All Keys</SelectItem>
          {MUSICAL_KEYS.map(key => (
            <SelectItem key={key} value={key}>{key}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* BPM Filter */}
      <Select
        value={bpmMin && bpmMax ? `${bpmMin}-${bpmMax}` : '__all__'}
        onValueChange={(v) => {
          if (v === '__all__') {
            onBpmChange(null, null);
          } else {
            const [min, max] = v.split('-').map(Number);
            onBpmChange(min, max);
          }
        }}
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="BPM" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All BPMs</SelectItem>
          {BPM_RANGES.map(range => (
            <SelectItem key={range.label} value={`${range.min}-${range.max}`}>
              {range.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Sort */}
      <div className="ml-auto">
        <Select value={sortBy} onValueChange={onSortChange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="created_at_desc">Newest</SelectItem>
            <SelectItem value="created_at_asc">Oldest</SelectItem>
            <SelectItem value="views_desc">Most Popular</SelectItem>
            <SelectItem value="bpm_asc">BPM (Low to High)</SelectItem>
            <SelectItem value="bpm_desc">BPM (High to Low)</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
```

### Step 2.5: Update Samples Page with Filters

**Location**: `frontend/app/components/features/samples-table.tsx`

```typescript
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/app/lib/api/client';
import { SearchBar } from './search-bar';
import { FilterBar } from './filter-bar';
import { ActiveFilters } from './active-filters';

export function SamplesTable() {
  const [search, setSearch] = useState('');
  const [bpmMin, setBpmMin] = useState<number | null>(null);
  const [bpmMax, setBpmMax] = useState<number | null>(null);
  const [musicalKey, setMusicalKey] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('created_at_desc');

  const { data, isLoading } = useQuery({
    queryKey: ['samples', search, bpmMin, bpmMax, musicalKey, sortBy],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (bpmMin) params.set('bpm_min', bpmMin.toString());
      if (bpmMax) params.set('bpm_max', bpmMax.toString());
      if (musicalKey) params.set('key', musicalKey);
      params.set('sort_by', sortBy);

      const response = await apiClient.get(`/samples?${params.toString()}`);
      return response.data;
    },
  });

  return (
    <div className="space-y-4">
      <SearchBar value={search} onChange={setSearch} />

      <FilterBar
        bpmMin={bpmMin}
        bpmMax={bpmMax}
        musicalKey={musicalKey}
        sortBy={sortBy}
        onBpmChange={(min, max) => { setBpmMin(min); setBpmMax(max); }}
        onKeyChange={setMusicalKey}
        onSortChange={setSortBy}
      />

      <ActiveFilters
        search={search}
        bpmMin={bpmMin}
        bpmMax={bpmMax}
        musicalKey={musicalKey}
        onClear={(filter) => {
          if (filter === 'search') setSearch('');
          if (filter === 'bpm') { setBpmMin(null); setBpmMax(null); }
          if (filter === 'key') setMusicalKey(null);
        }}
        onClearAll={() => {
          setSearch('');
          setBpmMin(null);
          setBpmMax(null);
          setMusicalKey(null);
        }}
      />

      {data && (
        <div className="text-sm text-muted-foreground">
          {data.total.toLocaleString()} results
        </div>
      )}

      {isLoading ? <div>Loading...</div> : (
        <div className="space-y-2">
          {data?.samples.map(sample => (
            <SampleRow key={sample.id} sample={sample} />
          ))}
        </div>
      )}
    </div>
  );
}
```

**✅ Phase 2 Complete: BPM and Key filters work!**

---

## Phase 3: Tag Filtering (Day 3)

### Step 3.1: Fix Tag Filtering Logic

**CRITICAL:** Use `&&` (overlap) not `@>` (contains)

**Location**: `backend/app/api/v1/endpoints/samples.py`

```python
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import ARRAY

class SampleSearchParams(BaseModel):
    # ... existing fields ...

    # NEW: Tag filtering
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags")

    @validator('tags')
    def validate_tags(cls, v):
        if v:
            tag_list = v.split(',')
            if len(tag_list) > 20:
                raise ValueError('Maximum 20 tags allowed')
        return v

# In search_samples function:
if params.tags:
    tag_list = [t.strip().lower() for t in params.tags.split(",")]
    # Use overlap operator: any tag matches (OR logic)
    query = query.where(
        Sample.tags.op('&&')(cast(tag_list, ARRAY(sa.String)))
    )
```

### Step 3.2: Add Popular Tags Endpoint

**Location**: `backend/app/api/v1/endpoints/samples.py`

```python
@router.get("/tags/popular", response_model=list[dict])
async def get_popular_tags(
    limit: int = Field(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most popular tags across all samples
    Returns list of {tag: str, count: int}
    """
    try:
        query = select(
            func.unnest(Sample.tags).label('tag'),
            func.count().label('count')
        ).where(
            Sample.status == "completed"
        ).group_by('tag').order_by(text('count DESC')).limit(limit)

        result = await asyncio.wait_for(
            db.execute(query),
            timeout=3.0
        )
        return [{"tag": row.tag, "count": row.count} for row in result]
    except asyncio.TimeoutError:
        logger.error("Popular tags query timeout")
        return []  # Return empty on timeout
```

### Step 3.3: Add Tag Pills Component

**Location**: `frontend/app/components/features/tag-pills.tsx`

```typescript
'use client';

import { Badge } from '@/app/components/ui/badge';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/app/lib/api/client';
import { cn } from '@/app/lib/utils';

interface TagPillsProps {
  activeTags: string[];
  onToggleTag: (tag: string) => void;
}

export function TagPills({ activeTags, onToggleTag }: TagPillsProps) {
  const { data: popularTags, isLoading } = useQuery({
    queryKey: ['tags', 'popular'],
    queryFn: async () => {
      const response = await apiClient.get('/samples/tags/popular?limit=30');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  if (isLoading || !popularTags) {
    return <div className="h-10 animate-pulse bg-muted rounded" />;
  }

  return (
    <div className="flex flex-wrap gap-2 py-4">
      {popularTags.map(({ tag, count }: any) => {
        const isActive = activeTags.includes(tag);

        return (
          <Badge
            key={tag}
            variant={isActive ? "default" : "outline"}
            className={cn(
              "cursor-pointer transition-colors",
              "hover:bg-primary hover:text-primary-foreground",
              isActive && "bg-primary text-primary-foreground"
            )}
            onClick={() => onToggleTag(tag)}
          >
            {tag}
            <span className="ml-1.5 text-xs opacity-70">{count}</span>
          </Badge>
        );
      })}
    </div>
  );
}
```

### Step 3.4: Update Samples Page with Tags

**Location**: `frontend/app/components/features/samples-table.tsx`

```typescript
export function SamplesTable() {
  const [search, setSearch] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [bpmMin, setBpmMin] = useState<number | null>(null);
  const [bpmMax, setBpmMax] = useState<number | null>(null);
  const [musicalKey, setMusicalKey] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('created_at_desc');

  const toggleTag = (tag: string) => {
    setTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const { data, isLoading } = useQuery({
    queryKey: ['samples', search, tags, bpmMin, bpmMax, musicalKey, sortBy],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (tags.length > 0) params.set('tags', tags.join(','));
      if (bpmMin) params.set('bpm_min', bpmMin.toString());
      if (bpmMax) params.set('bpm_max', bpmMax.toString());
      if (musicalKey) params.set('key', musicalKey);
      params.set('sort_by', sortBy);

      const response = await apiClient.get(`/samples?${params.toString()}`);
      return response.data;
    },
  });

  return (
    <div className="space-y-4">
      <SearchBar value={search} onChange={setSearch} />

      {/* NEW: Tag Pills */}
      <TagPills activeTags={tags} onToggleTag={toggleTag} />

      <FilterBar {...props} />

      {/* Update ActiveFilters to show tags */}
      <ActiveFilters
        search={search}
        tags={tags}
        bpmMin={bpmMin}
        bpmMax={bpmMax}
        musicalKey={musicalKey}
        onRemoveTag={(tag) => setTags(prev => prev.filter(t => t !== tag))}
        // ... other handlers
      />

      {/* ... rest of component ... */}
    </div>
  );
}
```

**✅ Phase 3 Complete: Tag filtering works!**

---

## Phase 4: Polish & Production (Day 4)

### Step 4.1: Add Active Filters Component

**Location**: `frontend/app/components/features/active-filters.tsx`

```typescript
'use client';

import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { X } from 'lucide-react';

interface ActiveFiltersProps {
  search: string;
  tags: string[];
  bpmMin: number | null;
  bpmMax: number | null;
  musicalKey: string | null;
  onRemoveTag: (tag: string) => void;
  onClear: (filter: string) => void;
  onClearAll: () => void;
}

export function ActiveFilters({
  search,
  tags,
  bpmMin,
  bpmMax,
  musicalKey,
  onRemoveTag,
  onClear,
  onClearAll,
}: ActiveFiltersProps) {
  const hasFilters = search || tags.length > 0 || bpmMin || bpmMax || musicalKey;

  if (!hasFilters) return null;

  return (
    <div className="flex items-center gap-2 py-3 flex-wrap">
      <span className="text-sm text-muted-foreground">Active filters:</span>

      {search && (
        <Badge variant="secondary" className="gap-2">
          Search: "{search}"
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onClear('search')}
          />
        </Badge>
      )}

      {tags.map(tag => (
        <Badge key={tag} variant="secondary" className="gap-2">
          {tag}
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onRemoveTag(tag)}
          />
        </Badge>
      ))}

      {(bpmMin || bpmMax) && (
        <Badge variant="secondary" className="gap-2">
          BPM: {bpmMin || 60}-{bpmMax || 180}
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onClear('bpm')}
          />
        </Badge>
      )}

      {musicalKey && (
        <Badge variant="secondary" className="gap-2">
          Key: {musicalKey}
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onClear('key')}
          />
        </Badge>
      )}

      <Button variant="ghost" size="sm" onClick={onClearAll} className="ml-2">
        Clear all
      </Button>
    </div>
  );
}
```

### Step 4.2: Performance Testing

**Test script**: `backend/scripts/test_search_performance.py`

```python
import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.api.v1.endpoints.samples import search_samples
from app.schemas.sample import SampleSearchParams

async def test_search_performance():
    engine = create_async_engine(DATABASE_URL)

    test_cases = [
        {"search": "house"},
        {"search": "house", "bpm_min": 120, "bpm_max": 130},
        {"tags": "house,techno"},
        {"search": "beyonce", "key": "C Major"},
    ]

    for params in test_cases:
        start = time.time()

        async with AsyncSession(engine) as db:
            result = await search_samples(
                SampleSearchParams(**params),
                db
            )

        duration = time.time() - start
        print(f"Query: {params}")
        print(f"Results: {result.total}")
        print(f"Time: {duration:.3f}s")

        if duration > 0.2:
            print("⚠️  SLOW QUERY!")
        print()

asyncio.run(test_search_performance())
```

### Step 4.3: Load Testing

```bash
# Install hey (HTTP load tester)
brew install hey  # macOS
# or download from: https://github.com/rakyll/hey

# Test search endpoint
hey -n 100 -c 10 "http://localhost:8000/api/v1/samples?search=house"

# Expected results:
# - Average response time: <200ms
# - 95th percentile: <500ms
# - 0 errors
```

---

## Testing Checklist (Comprehensive)

### Backend Tests

**Migration Tests:**
- [ ] Migration runs successfully: `alembic upgrade head`
- [ ] Column added: `psql $DATABASE_URL -c "\d samples"` shows `search_vector` column
- [ ] Trigger created: `psql $DATABASE_URL -c "\df update_search_vector"` shows function
- [ ] Backfill script runs: `python scripts/backfill_search_vectors.py`
- [ ] Index created: `psql $DATABASE_URL -c "\di ix_samples_search_vector"` shows index
- [ ] All samples have vectors: `SELECT COUNT(*) FROM samples WHERE search_vector IS NOT NULL;` equals total count

**API Tests:**
- [ ] Search endpoint: `curl "http://localhost:8000/api/v1/samples?search=house"`
- [ ] Tag filtering: `curl "http://localhost:8000/api/v1/samples?tags=house,techno"`
- [ ] BPM filtering: `curl "http://localhost:8000/api/v1/samples?bpm_min=120&bpm_max=130"`
- [ ] Key filtering: `curl "http://localhost:8000/api/v1/samples?key=C%20Major"`
- [ ] Sorting: `curl "http://localhost:8000/api/v1/samples?sort_by=views_desc"`
- [ ] Popular tags: `curl "http://localhost:8000/api/v1/samples/tags/popular"`

**Performance Tests:**
- [ ] Search completes in <200ms with 10k samples
- [ ] Tag query completes in <100ms
- [ ] Popular tags query completes in <3s (or returns empty)
- [ ] 10 concurrent searches don't crash database

**Edge Case Tests:**
- [ ] Empty search returns all samples
- [ ] Search with special characters doesn't crash: `search=%22%27%25`
- [ ] Tag filtering with 20 tags works
- [ ] BPM filter with min > max returns validation error
- [ ] Limit > 100 is rejected
- [ ] Skip > 10000 is rejected
- [ ] Samples without BPM/key are searchable (null handling)

### Frontend Tests

- [ ] Search bar appears and functions
- [ ] Typing triggers debounced API call (300ms delay)
- [ ] Popular tags load and display
- [ ] Clicking tags toggles active state
- [ ] BPM filter dropdown works
- [ ] Key dropdown works
- [ ] Sort dropdown updates results
- [ ] Active filters display correctly
- [ ] Clicking X removes individual filter
- [ ] "Clear all" button resets all filters
- [ ] Results count displays correctly
- [ ] Loading state shows while fetching
- [ ] Empty state shows when no results

### Integration Tests

- [ ] Search → Filter → Sort flow works
- [ ] URL params update (optional)
- [ ] Browser back/forward works (if using URL params)
- [ ] Mobile responsive
- [ ] Dark mode support

---

## Performance Optimization

### Backend

1. **Monitor indexes**: `EXPLAIN ANALYZE` on slow queries
2. **Connection pooling**: Check asyncpg pool size
3. **Query caching**: Consider Redis for popular tags (later)

### Frontend

1. **Debounce implemented**: ✅ 300ms
2. **TanStack Query caching**: ✅ 30s stale time
3. **Component memoization**: Use `React.memo` for SampleRow if needed

---

## Success Criteria (V1)

V1 is complete when:
- ✅ Text search returns relevant results in <200ms
- ✅ Users can filter by BPM range (preset options)
- ✅ Users can filter by musical key (24 options)
- ✅ Users can filter by tags (popular tags)
- ✅ Active filters display with clear buttons
- ✅ Sort by newest, most popular, BPM works
- ✅ Search works on 10k+ samples without timeout
- ✅ Error states handled gracefully
- ✅ Works on mobile and desktop
- ✅ No Zustand dependency (just React state + TanStack Query)
- ✅ No facets (deferred to Elasticsearch phase)

---

## Future Enhancements (Defer to V2+)

**Phase 3: LLM-Powered Tagging** (3-5 days)
- Auto-generate genres, moods, energy levels
- See `TAGGING_SEARCH_APPROACHES.md` Approach 5

**Phase 4: Semantic Search** (5-7 days)
- Install pgvector extension
- Generate embeddings for "vibe-based" search
- See `TAGGING_SEARCH_APPROACHES.md` Approach 4

**Phase 5: Elasticsearch** (1-2 weeks)
- Faceted search with counts (this is where facets belong!)
- Advanced analytics
- Scale to millions of samples
- See `TAGGING_SEARCH_APPROACHES.md` Approach 3

---

## Resources

- Backend reference: `backend/app/api/v1/endpoints/samples.py`
- Search approaches: `TAGGING_SEARCH_APPROACHES.md`
- PostgreSQL FTS docs: https://www.postgresql.org/docs/current/textsearch.html
- TanStack Query: https://tanstack.com/query/latest

---

## Key Differences from Original Plan

✅ **REMOVED:**
- Faceted search (500ms+ per request)
- Zustand store (unnecessary complexity)
- GENERATED ALWAYS column (doesn't backfill)
- @> operator for tags (wrong logic)
- Duration/views filters (not critical for V1)

✅ **ADDED:**
- Trigger-based tsvector with backfill
- && operator for tags (OR logic)
- Error handling and timeouts
- Input validation
- Performance logging
- Incremental delivery (Day 1-4)

✅ **SIMPLIFIED:**
- React state instead of Zustand
- Hard-coded filter options instead of dynamic facets
- Clear success criteria for each phase
