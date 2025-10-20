# Tagging System

A comprehensive tagging system for organizing and discovering TikTok audio samples.

## Features

### 🏷️ Tag Categories
- **Genre**: hip-hop, edm, pop, rock, trap, etc.
- **Mood**: energetic, chill, dark, happy, sad, etc.
- **Instrument**: piano, guitar, drums, synth, 808, etc.
- **Content**: dance, viral, trending, comedy, tutorial, etc.
- **Tempo**: slow, medium, fast, upbeat
- **Effect**: reverb, distorted, lofi, clean, etc.

### 🤖 Automatic Tag Generation
Tags are automatically generated during video processing based on:
- **BPM Analysis**: Tempo-based tags (slow, fast, upbeat) and genre hints
- **Musical Key**: Mood tags based on major/minor keys
- **TikTok Metadata**: Keywords from video descriptions
- **Engagement Metrics**: Viral/trending tags for high-view content
- **Genre Metadata**: Automatic genre tagging

High-confidence tags (≥70% confidence) are automatically added to samples.

### 📊 Tag Management

#### Backend API Endpoints
```
GET    /api/v1/tags                          # List all tags
GET    /api/v1/tags/popular                  # Get popular tags
GET    /api/v1/tags/{tag_id}                 # Get specific tag
POST   /api/v1/tags                          # Create tag (admin)
PATCH  /api/v1/tags/{tag_id}                 # Update tag (admin)
DELETE /api/v1/tags/{tag_id}                 # Delete tag (admin)

GET    /api/v1/tags/samples/{sample_id}/tags           # Get sample tags
POST   /api/v1/tags/samples/{sample_id}/tags           # Add tags to sample
DELETE /api/v1/tags/samples/{sample_id}/tags/{tag_name} # Remove tag from sample
GET    /api/v1/tags/samples/{sample_id}/suggestions    # Get AI-suggested tags
```

#### Sample Filtering
Filter samples by tags:
```
GET /api/v1/samples?tags=hip-hop,energetic
```

### 🎨 Frontend Components

#### TagBadge
Displays a single tag with category-specific colors:
```tsx
<TagBadge tag={tag} onRemove={() => {}} size="sm" />
```

#### TagList
Displays multiple tags with optional max display limit:
```tsx
<TagList tags={sample.tag_objects} maxDisplay={3} size="sm" />
```

### 🗄️ Database Schema

#### Tags Table
- `id`: UUID (primary key)
- `name`: Normalized tag name (unique, indexed)
- `display_name`: Original casing preserved
- `category`: Tag category enum
- `usage_count`: Number of samples using this tag (indexed)
- `created_at`, `updated_at`: Timestamps

#### Sample_Tags Junction Table
- Many-to-many relationship between samples and tags
- Cascading deletes for referential integrity

### 🔍 Tag Suggestion Algorithm

The system analyzes multiple factors to suggest relevant tags:

1. **BPM Analysis** (0.85 confidence)
   - < 90 BPM → slow, chill
   - 90-120 BPM → medium
   - 120-140 BPM → upbeat, dance
   - 140+ BPM → fast, energetic

2. **Genre Detection** (0.6-0.65 confidence)
   - 60-80 BPM → hip-hop
   - 120-130 BPM → house
   - 140-150 BPM → trap
   - 170+ BPM → drum-and-bass

3. **Musical Key** (0.6 confidence)
   - Minor keys → dark mood

4. **Description Analysis** (0.7-0.75 confidence)
   - Keyword matching for genres, moods, instruments, content types

5. **Engagement Metrics** (0.75-0.85 confidence)
   - 1M+ views → viral
   - 500K+ views or 50K+ likes → trending

### 📈 Usage Examples

#### Get Popular Tags
```typescript
const { tags } = await getPopularTags(30);
```

#### Search Tags
```typescript
const tags = await searchTags('hip');  // Returns: hip-hop, etc.
```

#### Get Tag Suggestions
```typescript
const { suggestions } = await getTagSuggestions(sampleId);
// Returns sorted list of suggestions with confidence scores
```

#### Add Tags to Sample
```typescript
await addTagsToSample(sampleId, ['hip-hop', 'energetic', 'viral']);
```

#### Remove Tag from Sample
```typescript
await removeTagFromSample(sampleId, 'hip-hop');
```

### 🚀 Automatic Processing Pipeline

The Inngest processing pipeline now includes an automatic tagging step:

1. Download video ✓
2. Extract audio ✓
3. Generate waveform ✓
4. Analyze audio (BPM, key) ✓
5. Update database ✓
6. **Generate and add tags** ← NEW
7. Cleanup temporary files ✓

### 🎯 Tag Categories & Colors (Frontend)

- **Genre** (purple): Music genre classifications
- **Mood** (blue): Emotional tone and atmosphere
- **Instrument** (green): Musical instruments featured
- **Content** (orange): TikTok content type
- **Tempo** (red): Speed and rhythm
- **Effect** (yellow): Audio processing effects
- **Other** (gray): Uncategorized tags

### 💡 Best Practices

1. **Tag Normalization**: Tags are automatically normalized (lowercase, hyphenated)
2. **Auto-Categorization**: Tags are automatically placed in appropriate categories
3. **Usage Tracking**: Tag popularity is tracked for discovery features
4. **High Confidence**: Only tags with ≥70% confidence are auto-added
5. **No Duplicates**: The system prevents duplicate tags on samples

### 🔧 Configuration

Tags are configured in `app/services/tag_service.py`:
- Predefined tag lists for each category
- Categorization rules
- Suggestion confidence thresholds
- BPM-to-genre mappings

### 🛠️ Database Migration

Migration file: `backend/alembic/versions/2b91c4fd5e8a_add_tag_model_and_sample_tags_junction_table.py`

To apply the migration:
```bash
cd backend
alembic upgrade head
```

### 📝 Notes

- **Backward Compatibility**: The legacy `tags` JSON field is preserved
- **Performance**: Tags are eager-loaded with samples for efficiency
- **Filtering**: Multiple tags can be filtered (AND logic)
- **Search**: Tag search supports partial matching on both name and display_name
