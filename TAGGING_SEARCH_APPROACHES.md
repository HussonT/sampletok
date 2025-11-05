# Tagging & Search System: Approaches & Recommendations

## Executive Summary

This document outlines different approaches for implementing a comprehensive tagging and search system for SampleTok. The goal is to make TikTok audio samples searchable by:
- **Structured data**: BPM, key, duration, creator, view counts
- **Tags**: Auto-extracted hashtags + manual categorization
- **Vibe/semantic search**: Natural language queries like "energetic summer vibes"

**Current State**: Basic ILIKE search on description/creator, automated tag extraction, BPM/key detection already working but not searchable.

**Recommended Path**: Start simple (Approach 1 → 2), then expand to semantic search (Approach 4) as user base grows.

---

## Approach 1: Enhanced PostgreSQL with JSONB Queries

**Description**: Extend current PostgreSQL implementation with proper filtering on existing fields.

### What You Already Have
- PostgreSQL database with indexed fields
- `tags` column (JSONB array) auto-populated from hashtags
- `bpm` (integer) and `key` (string) from audio analysis
- Indexed `creator_username` and `description` fields

### Implementation

**Backend Changes** (`app/api/v1/endpoints/samples.py`):

```python
# Add new query parameters
@router.get("/", response_model=SampleListResponse)
async def list_samples(
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    genre: str | None = None,
    tags: str | None = None,  # NEW: comma-separated tags
    bpm_min: int | None = None,  # NEW
    bpm_max: int | None = None,  # NEW
    key: str | None = None,  # NEW: e.g., "C Major"
    duration_min: float | None = None,  # NEW
    duration_max: float | None = None,  # NEW
    views_min: int | None = None,  # NEW
    views_max: int | None = None,  # NEW
    sort_by: str = "created_at_desc",  # NEW
    db: AsyncSession = Depends(get_db),
):
    query = select(Sample).where(Sample.status == "completed")

    # Existing search
    if search:
        query = query.where(
            Sample.description.ilike(f"%{search}%") |
            Sample.creator_username.ilike(f"%{search}%")
        )

    # NEW: Tag filtering (JSONB contains)
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",")]
        # PostgreSQL JSONB contains operator: @>
        query = query.where(Sample.tags.op('@>')(tag_list))

    # NEW: BPM range
    if bpm_min:
        query = query.where(Sample.bpm >= bpm_min)
    if bpm_max:
        query = query.where(Sample.bpm <= bpm_max)

    # NEW: Key filter
    if key:
        query = query.where(Sample.key == key)

    # NEW: Duration range
    if duration_min:
        query = query.where(Sample.duration_seconds >= duration_min)
    if duration_max:
        query = query.where(Sample.duration_seconds <= duration_max)

    # NEW: View count range
    if views_min:
        query = query.where(Sample.view_count >= views_min)
    if views_max:
        query = query.where(Sample.view_count <= views_max)

    # NEW: Sorting
    if sort_by == "bpm_asc":
        query = query.order_by(Sample.bpm.asc())
    elif sort_by == "views_desc":
        query = query.order_by(Sample.view_count.desc())
    # ... etc

    return await query.offset(skip).limit(limit).all()
```

**Database Indexes Needed**:

```python
# Migration: Add indexes for new filters
op.create_index('ix_samples_bpm', 'samples', ['bpm'])
op.create_index('ix_samples_key', 'samples', ['key'])
op.create_index('ix_samples_duration', 'samples', ['duration_seconds'])
op.create_index('ix_samples_view_count', 'samples', ['view_count'])

# GIN index for JSONB tag queries (very important!)
op.execute('CREATE INDEX ix_samples_tags_gin ON samples USING GIN (tags)')
```

### Pros
✅ No new infrastructure needed
✅ Fast (PostgreSQL is already optimized)
✅ Low complexity - 1-2 days to implement
✅ Works great for exact/range queries
✅ JSONB tag queries are very fast with GIN index
✅ No additional costs

### Cons
❌ No relevance ranking for text search
❌ No typo tolerance ("hous" won't match "house")
❌ No semantic understanding ("chill vibes" won't work)
❌ Limited full-text search capabilities

### Cost
**Time**: 1-2 days
**Money**: $0 (using existing PostgreSQL)

### When to Use
- **Phase 1**: MVP for structured filtering
- When you have <100k samples
- When users know exact terms (BPM: 120-130, Key: C Major)

---

## Approach 2: PostgreSQL Full-Text Search (tsvector)

**Description**: Add PostgreSQL's native full-text search capabilities for better text matching and relevance ranking.

### How It Works

PostgreSQL's full-text search converts text into `tsvector` (document) and searches with `tsquery` (query). It supports:
- Stemming: "running", "runs", "ran" → "run"
- Stop word removal: "the", "and", "of" ignored
- Relevance ranking: `ts_rank()` scores results
- Multiple language support
- Phrase matching and proximity search

### Implementation

**1. Add tsvector column** (migration):

```sql
-- Add generated tsvector column
ALTER TABLE samples
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(creator_username, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'D')
) STORED;

-- GIN index for fast full-text search
CREATE INDEX ix_samples_search_vector ON samples USING GIN (search_vector);
```

**Explanation**:
- `setweight()`: A=title (highest priority), B=description, C=creator, D=tags
- `GENERATED ALWAYS`: Auto-updates when source columns change
- `GIN index`: Makes searches O(log n) instead of O(n)

**2. Update search query**:

```python
from sqlalchemy import func, text

@router.get("/", response_model=SampleListResponse)
async def list_samples(
    search: str | None = None,
    # ... other filters
):
    query = select(Sample).where(Sample.status == "completed")

    if search:
        # Convert search to tsquery
        ts_query = func.plainto_tsquery('english', search)

        # Filter by tsvector match
        query = query.where(
            Sample.search_vector.op('@@')(ts_query)
        )

        # Order by relevance rank (higher = more relevant)
        query = query.order_by(
            func.ts_rank(Sample.search_vector, ts_query).desc()
        )
    else:
        query = query.order_by(Sample.created_at.desc())

    return await query.offset(skip).limit(limit).all()
```

**3. Enhanced search features**:

```python
# Phrase search: "beyonce remix"
search = "beyonce remix"
ts_query = func.phraseto_tsquery('english', search)

# Boolean search: "house AND techno"
search = "house & techno"
ts_query = func.to_tsquery('english', search)

# OR search: "house OR techno"
search = "house | techno"
ts_query = func.to_tsquery('english', search)

# NOT search: "house AND NOT drill"
search = "house & !drill"
ts_query = func.to_tsquery('english', search)

# Prefix search: "beyon*" matches "beyonce"
search = "beyon:*"
ts_query = func.to_tsquery('english', search)
```

### Search Examples

| User Query | Matches |
|-----------|---------|
| "beyonce" | title/description/tags containing "beyonce" |
| "beyonce acoustic" | Samples with BOTH terms (ranked by relevance) |
| "running run ran" | All match "run" stem |
| "house music" | Samples about house music (ranked by term frequency) |
| "drill beat 140 bpm" | Full-text + combine with BPM filter |

### Pros
✅ Built into PostgreSQL (no new infra)
✅ Relevance ranking with `ts_rank()`
✅ Stemming and language support
✅ Fast with GIN indexes
✅ Combines with structured filters (BPM, key, tags)
✅ Free (part of PostgreSQL)

### Cons
❌ No typo tolerance ("hous" won't match "house")
❌ No semantic search ("chill vibes" = literal match only)
❌ Language-specific (English only unless configured)
❌ Query syntax can be complex for advanced users

### Cost
**Time**: 2-3 days (migration + query updates)
**Money**: $0 (using existing PostgreSQL)

### When to Use
- **Phase 2**: After basic filtering is working
- When you need better text search than ILIKE
- When you want relevance ranking
- When you have <500k samples

### Performance
- Full-text search: ~5-20ms for 100k samples (with GIN index)
- Combines with filters: ~10-50ms
- Scales to 1M+ samples with proper indexing

---

## Approach 3: Elasticsearch

**Description**: Dedicated search engine for advanced full-text search, faceted search, and analytics.

### What Is Elasticsearch?

Elasticsearch is a distributed search and analytics engine built on Apache Lucene. It excels at:
- Full-text search with advanced features
- Faceted search (show counts per category)
- Aggregations (analytics, histograms)
- Near real-time search
- Horizontal scaling

### Architecture

```
PostgreSQL (source of truth)
    ↓ (on sample create/update)
Sync to Elasticsearch index
    ↓ (on search request)
Elasticsearch returns results + facets
    ↓ (fetch full data)
PostgreSQL returns complete sample objects
```

**Key Concept**: Elasticsearch is a **search index**, not your database. PostgreSQL remains the source of truth.

### Implementation

**1. Setup Elasticsearch**:

```bash
# Option A: Elastic Cloud (managed)
# Sign up at https://cloud.elastic.co
# Create deployment (starts at $95/month)

# Option B: Self-hosted (Docker)
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  elasticsearch:8.11.0
```

**2. Define index mapping**:

```python
# app/services/search/elasticsearch_config.py

SAMPLE_INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "hashtag_analyzer": {
                    "type": "custom",
                    "tokenizer": "keyword",
                    "filter": ["lowercase"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "english"},
            "description": {"type": "text", "analyzer": "english"},
            "creator_username": {"type": "keyword"},
            "tags": {
                "type": "text",
                "analyzer": "hashtag_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"}  # For exact match
                }
            },
            "bpm": {"type": "integer"},
            "key": {"type": "keyword"},
            "duration_seconds": {"type": "float"},
            "view_count": {"type": "integer"},
            "genre": {"type": "keyword"},
            "created_at": {"type": "date"},
            # Nested object for faceted search
            "audio_features": {
                "type": "nested",
                "properties": {
                    "bpm_range": {"type": "keyword"},  # "120-130"
                    "key_family": {"type": "keyword"}  # "C", "A", etc.
                }
            }
        }
    }
}
```

**3. Sync samples to Elasticsearch**:

```python
# app/services/search/elasticsearch_service.py

from elasticsearch import AsyncElasticsearch

class ElasticsearchService:
    def __init__(self):
        self.es = AsyncElasticsearch(
            hosts=[os.getenv("ELASTICSEARCH_URL")],
            api_key=os.getenv("ELASTICSEARCH_API_KEY")
        )

    async def index_sample(self, sample: Sample):
        """Index a sample in Elasticsearch"""
        doc = {
            "id": sample.id,
            "title": sample.title,
            "description": sample.description,
            "creator_username": sample.creator_username,
            "tags": sample.tags or [],
            "bpm": sample.bpm,
            "key": sample.key,
            "duration_seconds": sample.duration_seconds,
            "view_count": sample.view_count,
            "genre": sample.genre,
            "created_at": sample.created_at.isoformat(),
            "audio_features": {
                "bpm_range": self._get_bpm_range(sample.bpm),
                "key_family": sample.key.split()[0] if sample.key else None
            }
        }

        await self.es.index(
            index="samples",
            id=sample.id,
            document=doc
        )

    def _get_bpm_range(self, bpm: int) -> str:
        """Bucket BPM for faceted search"""
        if bpm < 90: return "60-90"
        elif bpm < 120: return "90-120"
        elif bpm < 150: return "120-150"
        else: return "150+"
```

**4. Trigger indexing on sample creation**:

```python
# app/inngest_functions.py

@inngest.create_function(
    fn_id="update-database",
    # ...
)
async def update_database(ctx, step):
    # ... existing code to update PostgreSQL

    # NEW: Index in Elasticsearch
    await step.run("index-in-elasticsearch", lambda:
        elasticsearch_service.index_sample(sample)
    )
```

**5. Search with facets**:

```python
# app/services/search/elasticsearch_service.py

async def search_samples(
    query: str = None,
    tags: list[str] = None,
    bpm_min: int = None,
    bpm_max: int = None,
    key: str = None,
    skip: int = 0,
    limit: int = 20
) -> dict:
    """Search samples with faceted navigation"""

    # Build Elasticsearch query
    must_clauses = []
    filter_clauses = []

    # Full-text search
    if query:
        must_clauses.append({
            "multi_match": {
                "query": query,
                "fields": ["title^3", "description^2", "tags"],
                "fuzziness": "AUTO",  # Typo tolerance!
                "type": "best_fields"
            }
        })

    # Tag filter
    if tags:
        filter_clauses.append({
            "terms": {"tags.keyword": tags}
        })

    # BPM range
    if bpm_min or bpm_max:
        range_filter = {}
        if bpm_min: range_filter["gte"] = bpm_min
        if bpm_max: range_filter["lte"] = bpm_max
        filter_clauses.append({"range": {"bpm": range_filter}})

    # Key filter
    if key:
        filter_clauses.append({"term": {"key": key}})

    # Execute search with aggregations (facets)
    response = await self.es.search(
        index="samples",
        body={
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            },
            "from": skip,
            "size": limit,
            "sort": [{"_score": "desc"}, {"created_at": "desc"}],
            # FACETED SEARCH: Get counts per category
            "aggs": {
                "tags": {
                    "terms": {"field": "tags.keyword", "size": 50}
                },
                "bpm_ranges": {
                    "terms": {"field": "audio_features.bpm_range"}
                },
                "keys": {
                    "terms": {"field": "key", "size": 24}  # 12 notes × 2 modes
                },
                "genres": {
                    "terms": {"field": "genre"}
                },
                "avg_bpm": {
                    "avg": {"field": "bpm"}
                }
            }
        }
    )

    return {
        "total": response["hits"]["total"]["value"],
        "samples": [hit["_source"]["id"] for hit in response["hits"]["hits"]],
        "facets": {
            "tags": response["aggregations"]["tags"]["buckets"],
            "bpm_ranges": response["aggregations"]["bpm_ranges"]["buckets"],
            "keys": response["aggregations"]["keys"]["buckets"],
            "genres": response["aggregations"]["genres"]["buckets"],
        },
        "analytics": {
            "avg_bpm": response["aggregations"]["avg_bpm"]["value"]
        }
    }
```

**6. API endpoint**:

```python
@router.get("/search", response_model=SearchResponse)
async def search_samples(
    query: str = None,
    tags: str = None,  # comma-separated
    bpm_min: int = None,
    bpm_max: int = None,
    key: str = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    # Search in Elasticsearch
    es_results = await elasticsearch_service.search_samples(
        query=query,
        tags=tags.split(",") if tags else None,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        key=key,
        skip=skip,
        limit=limit
    )

    # Fetch full sample data from PostgreSQL
    sample_ids = es_results["samples"]
    samples = await db.execute(
        select(Sample).where(Sample.id.in_(sample_ids))
    )

    return {
        "samples": samples.all(),
        "total": es_results["total"],
        "facets": es_results["facets"],  # For frontend filters
        "analytics": es_results["analytics"]
    }
```

### Search Examples

| Feature | Example |
|---------|---------|
| Full-text | "beyonce acoustic" |
| Fuzzy match | "byonce" → matches "beyonce" |
| Phrase | "house music" (exact phrase) |
| Tags | tags=["beyonce", "house"] |
| BPM range | bpm_min=120, bpm_max=130 |
| Combined | "energetic" + bpm>140 + key="C Major" |
| Faceted nav | Show "127 samples in 120-130 BPM range" |

### Pros
✅ **Best-in-class full-text search**
✅ **Typo tolerance** (fuzziness: "hous" → "house")
✅ **Faceted search** (show counts per filter)
✅ **Advanced analytics** (avg BPM, histograms)
✅ **Scales horizontally** (handles millions of samples)
✅ **Fast** (typically <50ms for complex queries)
✅ **Rich query DSL** (nested queries, geo-search, etc.)

### Cons
❌ **Additional infrastructure** to manage
❌ **Cost**: $95+/month (Elastic Cloud) or server costs
❌ **Complexity**: Need to sync PostgreSQL ↔ Elasticsearch
❌ **Data duplication** (same data in 2 systems)
❌ **No semantic understanding** ("chill vibes" = literal match)

### Cost
**Time**: 1-2 weeks (setup, sync logic, testing)
**Money**:
- Elastic Cloud: $95-500/month (based on data volume)
- Self-hosted: $20-100/month (VPS/server costs)

### When to Use
- **Phase 3-4**: After you have >100k samples
- When you need faceted search (critical for discovery UX)
- When you want advanced analytics
- When PostgreSQL full-text search isn't enough
- When you have budget for infrastructure

### Alternatives to Elasticsearch
- **Meilisearch**: Easier to use, typo-tolerant, $0 self-hosted, no facets
- **Typesense**: Fast, typo-tolerant, easier than Elasticsearch, good facets
- **Algolia**: Managed, very fast, expensive ($1/1k searches after free tier)

---

## Approach 4: Semantic Search with Vector Embeddings

**Description**: Use AI embeddings to understand the *meaning* of queries, enabling "vibe-based" search.

### The Problem with Traditional Search

Traditional search (even Elasticsearch) only matches **keywords**:
- Query: "chill summer vibes"
- Traditional: Looks for samples with "chill", "summer", "vibes" in text
- Problem: Misses samples with similar vibes described differently ("relaxed beach energy", "laid-back sunny day")

### How Semantic Search Works

1. **Generate embeddings**: Convert text → vector of numbers (e.g., 1536 dimensions)
2. **Similar vectors = similar meaning**: "happy upbeat energetic" and "joyful exciting vibrant" have similar vectors
3. **Find nearest neighbors**: Given query vector, find samples with closest vectors

```
Text: "chill summer vibes"
   ↓ (OpenAI embedding model)
Vector: [0.021, -0.134, 0.891, ..., 0.456]  (1536 numbers)
   ↓ (cosine similarity search)
Top matches:
  - "relaxed beach energy" (similarity: 0.92)
  - "laid-back sunny day" (similarity: 0.89)
  - "mellow tropical feels" (similarity: 0.87)
```

### Implementation Options

#### Option 4A: PostgreSQL + pgvector Extension

**Best for**: Getting started with semantic search, <500k samples

```sql
-- Install pgvector extension
CREATE EXTENSION vector;

-- Add embedding column to samples
ALTER TABLE samples
ADD COLUMN description_embedding vector(1536);

-- Create index for fast similarity search
CREATE INDEX ON samples USING ivfflat (description_embedding vector_cosine_ops);
```

```python
# Generate embedding for sample
import openai

async def generate_embedding(text: str) -> list[float]:
    response = await openai.Embedding.create(
        model="text-embedding-3-small",  # $0.02 per 1M tokens
        input=text
    )
    return response['data'][0]['embedding']

# During sample processing
sample_text = f"{sample.title} {sample.description} {' '.join(sample.tags)}"
sample.description_embedding = await generate_embedding(sample_text)

# Search by semantic similarity
query = "chill summer vibes"
query_embedding = await generate_embedding(query)

results = await db.execute(
    select(Sample)
    .order_by(Sample.description_embedding.cosine_distance(query_embedding))
    .limit(20)
)
```

**Pros**:
✅ No additional infrastructure (uses PostgreSQL)
✅ Understands meaning, not just keywords
✅ Works for "vibe" queries
✅ Combines with structured filters (BPM, key)

**Cons**:
❌ Embedding generation costs ($0.02 per 1M tokens)
❌ Slower than keyword search (~100-500ms)
❌ Requires re-embedding all samples when model updates
❌ pgvector performance degrades at >500k vectors

**Cost**:
- Embedding generation: ~$1-5 for 10k samples (one-time per sample)
- Search: Free (uses PostgreSQL)

#### Option 4B: Pinecone (Managed Vector Database)

**Best for**: Large-scale semantic search (>500k samples)

```python
import pinecone

# Initialize Pinecone
pinecone.init(api_key="...", environment="us-west1-gcp")
index = pinecone.Index("samples")

# Index sample
sample_text = f"{sample.title} {sample.description} {' '.join(sample.tags)}"
embedding = await generate_embedding(sample_text)

index.upsert(vectors=[{
    "id": str(sample.id),
    "values": embedding,
    "metadata": {
        "bpm": sample.bpm,
        "key": sample.key,
        "tags": sample.tags,
        "view_count": sample.view_count
    }
}])

# Search with filters
query_embedding = await generate_embedding("chill summer vibes")

results = index.query(
    vector=query_embedding,
    top_k=20,
    filter={
        "bpm": {"$gte": 90, "$lte": 120},
        "tags": {"$in": ["house", "electronic"]}
    }
)
```

**Pros**:
✅ Very fast (<50ms) even for millions of vectors
✅ Built-in filtering on metadata
✅ Managed service (no infrastructure)
✅ Scales automatically

**Cons**:
❌ Additional service to manage
❌ Cost: $70+/month for production workloads
❌ Still need PostgreSQL as source of truth

#### Option 4C: Weaviate (Open Source Vector DB)

**Best for**: Self-hosting semantic search, budget-conscious

Similar to Pinecone but open source. Can self-host or use Weaviate Cloud.

### Hybrid Search: Best of Both Worlds

Combine keyword search + semantic search for optimal results:

```python
# Elasticsearch for keyword match
keyword_results = await es.search("house music", bpm_min=120)

# Pinecone for semantic match
semantic_results = await pinecone.query("energetic club vibes", bpm_min=120)

# Merge results with weighted scoring
final_results = merge_and_rank(
    keyword_results, weight=0.6,
    semantic_results, weight=0.4
)
```

**Why Hybrid?**
- Query: "dril beat" → Keyword search catches typo better
- Query: "aggressive dark energy" → Semantic search understands vibe
- Combine both: Get precision of keywords + recall of semantics

### Pros (Semantic Search Overall)
✅ **Understands meaning**: "chill vibes" matches "relaxed energy"
✅ **Multilingual**: Works across languages naturally
✅ **Typo-tolerant**: Embeddings capture intent despite typos
✅ **Discovery**: Find samples users wouldn't find with keywords
✅ **User-friendly**: Natural language queries

### Cons
❌ **Cost**: Embedding generation + vector DB costs
❌ **Complexity**: Need embedding pipeline
❌ **Slower**: 50-500ms vs 5-20ms for keyword search
❌ **Black box**: Harder to debug why results ranked that way

### Cost
**Time**: 1-2 weeks
**Money**:
- pgvector: $1-10/month (embeddings only)
- Pinecone: $70-200/month
- Weaviate self-hosted: $20-50/month (server)

### When to Use
- **Phase 4+**: After basic search is working well
- When users struggle to find samples with keywords
- When "vibe-based" discovery is core to UX
- When you have budget for embedding costs

---

## Approach 5: LLM-Powered Tag Generation

**Description**: Use LLMs to auto-generate rich tags and metadata from audio samples.

### Concept

Instead of just extracting hashtags, use an LLM to:
1. Analyze sample description, title, and metadata
2. Generate structured tags: genre, mood, instruments, energy level, use cases
3. Store tags for filtering and search

### Implementation

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def generate_rich_tags(sample: Sample) -> dict:
    """Use LLM to generate rich tags from sample metadata"""

    prompt = f"""
    Analyze this TikTok audio sample and generate structured tags:

    Title: {sample.title}
    Description: {sample.description}
    Creator: {sample.creator_username}
    BPM: {sample.bpm}
    Key: {sample.key}
    Duration: {sample.duration_seconds}s
    View count: {sample.view_count}
    Hashtags: {', '.join(sample.tags)}

    Generate a JSON object with:
    - genres: array of 1-3 music genres
    - moods: array of 2-5 mood descriptors (e.g., "energetic", "melancholic")
    - instruments: array of detected instruments
    - energy_level: 1-10 scale
    - vocal_type: "male", "female", "instrumental", "mixed", or null
    - use_cases: array of use cases (e.g., "workout", "studying", "party")
    - vibe_keywords: array of 5-10 searchable keywords for "vibe" search

    Return only valid JSON.
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",  # Cheaper and fast
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    tags = json.loads(response.choices[0].message.content)
    return tags

# During sample processing (Inngest function)
rich_tags = await generate_rich_tags(sample)

sample.genres = rich_tags["genres"]  # Update model to support arrays
sample.moods = rich_tags["moods"]
sample.instruments = rich_tags["instruments"]
sample.energy_level = rich_tags["energy_level"]
sample.vocal_type = rich_tags["vocal_type"]
sample.use_cases = rich_tags["use_cases"]
sample.vibe_keywords = rich_tags["vibe_keywords"]
```

### Database Schema Updates

```python
# app/models/sample.py

class Sample(Base):
    # ... existing fields

    # Rich tags from LLM
    genres = Column(ARRAY(String), default=list)  # Multiple genres
    moods = Column(ARRAY(String), default=list)
    instruments = Column(ARRAY(String), default=list)
    energy_level = Column(Integer)  # 1-10
    vocal_type = Column(String)  # male/female/instrumental/mixed
    use_cases = Column(ARRAY(String), default=list)
    vibe_keywords = Column(ARRAY(String), default=list)
```

### Search Example

```python
# User query: "energetic workout music with female vocals"

filters = {
    "energy_level": {"gte": 7},
    "use_cases": ["workout"],
    "vocal_type": "female",
    "moods": ["energetic"]
}

results = await db.execute(
    select(Sample)
    .where(Sample.energy_level >= filters["energy_level"]["gte"])
    .where(Sample.use_cases.contains(filters["use_cases"]))
    .where(Sample.vocal_type == filters["vocal_type"])
    .where(Sample.moods.overlap(filters["moods"]))
    .limit(20)
)
```

### Pros
✅ **Rich metadata** without manual tagging
✅ **Consistent** tags across all samples
✅ **Searchable attributes** humans wouldn't extract
✅ **Structured data** (easy to filter/sort)
✅ **Auto-improves** as LLMs get better

### Cons
❌ **Cost**: ~$0.001-0.01 per sample (gpt-4o-mini)
❌ **Latency**: Adds 1-5 seconds to processing pipeline
❌ **Accuracy**: LLM might hallucinate tags
❌ **Rate limits**: OpenAI API has rate limits

### Cost
**Time**: 3-5 days (prompt engineering, testing)
**Money**:
- 10k samples: $10-100 (one-time, per sample)
- gpt-4o-mini: ~$0.001 per sample
- gpt-4o: ~$0.01 per sample

### When to Use
- **Phase 3+**: After basic tagging is working
- When hashtags are insufficient/inconsistent
- When you want rich, searchable metadata
- When you have budget for LLM API costs

### Optimization Tips
- Use `gpt-4o-mini` (10x cheaper than gpt-4o)
- Batch process during off-peak hours
- Cache results (don't regenerate on every update)
- Use structured outputs (JSON mode) for reliability

---

## Recommended Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Approach 1: Enhanced PostgreSQL**

**Goals**:
- Connect existing frontend filters to backend
- Make BPM, key, tags searchable
- Basic sorting and pagination

**Implementation**:
1. Add query parameters to `/api/v1/samples` endpoint
2. Add database indexes (bpm, key, tags GIN index)
3. Update frontend to send filter params
4. Test with existing data

**Deliverables**:
- Users can filter by: BPM range, key, tags, duration, view count
- Users can sort by: date, views, BPM, creator
- Search works on description + creator
- ~1-2 days of work

### Phase 2: Better Text Search (Week 3)
**Approach 2: PostgreSQL Full-Text Search**

**Goals**:
- Relevance ranking
- Stemming (search "running" finds "run", "ran")
- Better search quality

**Implementation**:
1. Add migration for `search_vector` tsvector column
2. Create GIN index
3. Update search query to use `ts_rank()`
4. Test with various search queries

**Deliverables**:
- Search quality improves significantly
- Results ranked by relevance
- Supports phrase search, boolean operators
- ~2-3 days of work

### Phase 3: Rich Tagging (Week 4-5)
**Approach 5: LLM-Powered Tag Generation**

**Goals**:
- Auto-generate rich tags for all samples
- Add genre, mood, energy level, use cases
- Make samples more discoverable

**Implementation**:
1. Update Sample model with new tag fields
2. Create migration
3. Add LLM tagging to Inngest pipeline
4. Backfill existing samples (background job)
5. Update frontend filters to use rich tags

**Deliverables**:
- Every sample has: genres, moods, energy level, use cases
- Users can filter by these attributes
- ~3-5 days of work
- Cost: ~$10-50 for backfilling existing samples

### Phase 4: Semantic Search (Month 2-3)
**Approach 4A: pgvector for Semantic Search**

**Goals**:
- Enable "vibe-based" search
- Users can describe what they want in natural language
- Find similar samples even if keywords don't match

**Implementation**:
1. Install pgvector extension
2. Add migration for embedding column
3. Generate embeddings for all samples
4. Add `/api/v1/search/semantic` endpoint
5. Update frontend with "Describe the vibe you're looking for" input

**Deliverables**:
- Users can search: "chill summer vibes", "aggressive dark energy"
- Results ranked by semantic similarity
- ~5-7 days of work
- Cost: ~$5-20 for initial embeddings

### Phase 5 (Optional): Elasticsearch (Month 4+)
**Approach 3: Elasticsearch**

**Goals**:
- Faceted search (show counts per filter option)
- Advanced analytics
- Scale to millions of samples

**Implementation**:
1. Set up Elasticsearch (Elastic Cloud or self-hosted)
2. Create index mapping
3. Sync PostgreSQL → Elasticsearch on sample create/update
4. Add `/api/v1/search/advanced` endpoint with facets
5. Update frontend with faceted navigation UI

**Deliverables**:
- Faceted search: "127 samples in 120-130 BPM" (click to filter)
- Analytics dashboard: avg BPM, popular tags, trending creators
- Handles 1M+ samples easily
- ~1-2 weeks of work
- Cost: $95-200/month (Elastic Cloud)

---

## Decision Matrix

| Approach | Complexity | Cost ($/mo) | Time to Implement | Best For |
|----------|-----------|-------------|-------------------|----------|
| **1. Enhanced PostgreSQL** | ⭐ Low | $0 | 1-2 days | MVP, <100k samples |
| **2. PostgreSQL FTS** | ⭐⭐ Medium | $0 | 2-3 days | Better search, <500k samples |
| **3. Elasticsearch** | ⭐⭐⭐⭐ High | $95-500 | 1-2 weeks | Faceted search, analytics, >100k samples |
| **4A. pgvector** | ⭐⭐⭐ Medium | $5-20 | 5-7 days | Vibe search, <500k samples |
| **4B. Pinecone** | ⭐⭐⭐ Medium | $70-200 | 5-7 days | Vibe search, >500k samples |
| **5. LLM Tagging** | ⭐⭐ Medium | $10-100 (one-time) | 3-5 days | Rich metadata generation |

---

## Frequently Asked Questions

### Q: Which approach should I start with?

**A**: Start with **Approach 1 (Enhanced PostgreSQL)** → **Approach 2 (FTS)** → **Approach 5 (LLM Tagging)** → **Approach 4 (Semantic Search)**.

This path:
- Delivers value quickly (1-2 days to first filters)
- Builds on existing infrastructure (PostgreSQL)
- Minimizes costs initially
- Allows learning what users actually need before investing in expensive infrastructure

### Q: Do I need Elasticsearch?

**A**: Not initially. PostgreSQL with full-text search handles 500k+ samples well. Only consider Elasticsearch when:
- You have >100k samples AND
- You need faceted search (critical for UX) AND
- PostgreSQL search feels slow (>200ms) AND
- You have budget ($100-500/month)

### Q: What about typo tolerance?

**A**:
- **Basic**: Use PostgreSQL trigram similarity (`pg_trgm` extension)
- **Better**: Use Elasticsearch fuzziness
- **Best**: Use semantic search (embeddings naturally handle typos)

### Q: How do I handle "vibe-based" search?

**A**:
1. **Phase 1**: Use LLM-generated `vibe_keywords` as tags (Approach 5)
2. **Phase 2**: Add semantic search with embeddings (Approach 4)
3. **Phase 3**: Hybrid search (keywords + semantics)

### Q: What's the total cost for the recommended path?

**A**:
- **Phase 1-2**: $0/month (PostgreSQL only)
- **Phase 3**: $10-50 one-time (LLM tagging backfill)
- **Phase 4**: $5-20/month (embedding generation)
- **Phase 5** (optional): $95-500/month (Elasticsearch)

**Total for Phases 1-4**: ~$10-30/month after initial setup

### Q: Can I combine multiple approaches?

**A**: Yes! Common combinations:
- **PostgreSQL FTS + pgvector**: Keyword search + semantic search
- **Elasticsearch + Pinecone**: Faceted search + semantic search
- **PostgreSQL + LLM tagging + pgvector**: Rich tags + semantic search

### Q: What about audio fingerprinting for "find similar sounds"?

**A**: This is different from text search. Options:
- **Essentia** (open source): Extract audio features, compare similarity
- **AcoustID**: Audio fingerprinting service
- **Musiio**: ML-based audio similarity API
- Combine with your semantic search for "sounds like this + feels like X"

---

## Next Steps

### Immediate Actions (This Week)

1. **Implement Approach 1** (1-2 days)
   - Add BPM, key, tag filtering to backend
   - Connect frontend filters
   - Test with existing data

2. **Add PostgreSQL FTS** (2-3 days)
   - Create migration for `search_vector`
   - Update search queries
   - Test search quality

### Short-term (Next 2-4 Weeks)

3. **Add LLM Tagging** (3-5 days)
   - Update Sample model
   - Add to Inngest pipeline
   - Backfill existing samples

4. **Monitor & Learn**
   - Track which filters users use most
   - Monitor search query patterns
   - Identify gaps in discoverability

### Medium-term (Month 2-3)

5. **Add Semantic Search** (5-7 days)
   - Install pgvector
   - Generate embeddings
   - Add semantic search endpoint

6. **Evaluate Elasticsearch**
   - If >100k samples OR need facets
   - Set up staging environment
   - Compare performance with PostgreSQL

---

## Resources

### PostgreSQL Full-Text Search
- [Official docs](https://www.postgresql.org/docs/current/textsearch.html)
- [Full-Text Search tutorial](https://www.compose.com/articles/mastering-postgresql-tools-full-text-search-and-phrase-search/)

### Elasticsearch
- [Elasticsearch Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)

### Vector Search
- [pgvector](https://github.com/pgvector/pgvector)
- [Pinecone](https://www.pinecone.io/)
- [Weaviate](https://weaviate.io/)

### Embeddings
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [Sentence Transformers](https://www.sbert.net/) (open source alternative)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-03
**Author**: Claude Code Research Agent