"""
Tag service for managing tags and generating suggestions
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from uuid import UUID
import re

from app.models.tag import Tag, TagCategory
from app.models.sample import Sample
from app.models.schemas import TagSuggestion, TagCategoryEnum


class TagService:
    """Service for tag operations and suggestions"""

    # Predefined tags for common categories
    GENRE_TAGS = {
        "hip-hop": "Hip-Hop",
        "rap": "Rap",
        "edm": "EDM",
        "pop": "Pop",
        "rock": "Rock",
        "electronic": "Electronic",
        "trap": "Trap",
        "house": "House",
        "techno": "Techno",
        "indie": "Indie",
        "r&b": "R&B",
        "jazz": "Jazz",
        "classical": "Classical",
        "country": "Country",
        "reggae": "Reggae",
        "latin": "Latin",
        "afrobeat": "Afrobeat",
        "drill": "Drill",
        "phonk": "Phonk",
    }

    MOOD_TAGS = {
        "energetic": "Energetic",
        "chill": "Chill",
        "dark": "Dark",
        "happy": "Happy",
        "sad": "Sad",
        "uplifting": "Uplifting",
        "aggressive": "Aggressive",
        "romantic": "Romantic",
        "melancholic": "Melancholic",
        "dreamy": "Dreamy",
        "intense": "Intense",
        "relaxing": "Relaxing",
        "mysterious": "Mysterious",
        "nostalgic": "Nostalgic",
    }

    INSTRUMENT_TAGS = {
        "piano": "Piano",
        "guitar": "Guitar",
        "drums": "Drums",
        "bass": "Bass",
        "synth": "Synth",
        "808": "808",
        "vocals": "Vocals",
        "strings": "Strings",
        "brass": "Brass",
        "flute": "Flute",
        "violin": "Violin",
        "saxophone": "Saxophone",
    }

    CONTENT_TAGS = {
        "dance": "Dance",
        "viral": "Viral",
        "trending": "Trending",
        "comedy": "Comedy",
        "tutorial": "Tutorial",
        "challenge": "Challenge",
        "lip-sync": "Lip Sync",
        "freestyle": "Freestyle",
        "remix": "Remix",
        "original": "Original",
        "cover": "Cover",
        "duet": "Duet",
        "transition": "Transition",
    }

    TEMPO_TAGS = {
        "slow": "Slow",
        "medium": "Medium",
        "fast": "Fast",
        "upbeat": "Upbeat",
    }

    EFFECT_TAGS = {
        "reverb": "Reverb",
        "distorted": "Distorted",
        "lofi": "Lo-Fi",
        "clean": "Clean",
        "compressed": "Compressed",
        "echo": "Echo",
        "filtered": "Filtered",
    }

    @staticmethod
    def normalize_tag_name(name: str) -> str:
        """Normalize tag name (lowercase, trim, remove extra spaces)"""
        return re.sub(r'\s+', '-', name.strip().lower())

    @staticmethod
    async def get_or_create_tag(
        db: AsyncSession,
        name: str,
        category: TagCategory = TagCategory.OTHER
    ) -> Tag:
        """Get existing tag or create new one"""
        normalized_name = TagService.normalize_tag_name(name)

        # Try to find existing tag
        result = await db.execute(
            select(Tag).where(Tag.name == normalized_name)
        )
        tag = result.scalar_one_or_none()

        if tag:
            return tag

        # Create new tag
        display_name = name.strip()
        tag = Tag(
            name=normalized_name,
            display_name=display_name,
            category=category
        )
        db.add(tag)
        await db.flush()
        return tag

    @staticmethod
    async def add_tags_to_sample(
        db: AsyncSession,
        sample: Sample,
        tag_names: List[str],
        auto_categorize: bool = True
    ) -> List[Tag]:
        """Add multiple tags to a sample"""
        added_tags = []

        for tag_name in tag_names:
            # Determine category if auto_categorize is True
            category = TagCategory.OTHER
            if auto_categorize:
                category = TagService._categorize_tag(tag_name)

            # Get or create tag
            tag = await TagService.get_or_create_tag(db, tag_name, category)

            # Add to sample if not already added
            if tag not in sample.tag_objects:
                sample.tag_objects.append(tag)
                tag.usage_count += 1
                added_tags.append(tag)

        await db.flush()
        return added_tags

    @staticmethod
    async def remove_tag_from_sample(
        db: AsyncSession,
        sample: Sample,
        tag_name: str
    ) -> bool:
        """Remove a tag from a sample"""
        normalized_name = TagService.normalize_tag_name(tag_name)

        for tag in sample.tag_objects:
            if tag.name == normalized_name:
                sample.tag_objects.remove(tag)
                tag.usage_count = max(0, tag.usage_count - 1)
                await db.flush()
                return True

        return False

    @staticmethod
    async def get_popular_tags(
        db: AsyncSession,
        limit: int = 50,
        category: Optional[TagCategory] = None
    ) -> List[Tag]:
        """Get popular tags ordered by usage count"""
        query = select(Tag).where(Tag.usage_count > 0)

        if category:
            query = query.where(Tag.category == category)

        query = query.order_by(Tag.usage_count.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def search_tags(
        db: AsyncSession,
        query: str,
        limit: int = 20
    ) -> List[Tag]:
        """Search tags by name"""
        normalized_query = TagService.normalize_tag_name(query)

        result = await db.execute(
            select(Tag)
            .where(
                or_(
                    Tag.name.ilike(f"%{normalized_query}%"),
                    Tag.display_name.ilike(f"%{query}%")
                )
            )
            .order_by(Tag.usage_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def _categorize_tag(tag_name: str) -> TagCategory:
        """Auto-categorize a tag based on its name"""
        normalized = TagService.normalize_tag_name(tag_name)

        if normalized in TagService.GENRE_TAGS:
            return TagCategory.GENRE
        elif normalized in TagService.MOOD_TAGS:
            return TagCategory.MOOD
        elif normalized in TagService.INSTRUMENT_TAGS:
            return TagCategory.INSTRUMENT
        elif normalized in TagService.CONTENT_TAGS:
            return TagCategory.CONTENT
        elif normalized in TagService.TEMPO_TAGS:
            return TagCategory.TEMPO
        elif normalized in TagService.EFFECT_TAGS:
            return TagCategory.EFFECT

        return TagCategory.OTHER

    @staticmethod
    async def generate_suggestions(
        db: AsyncSession,
        sample: Sample
    ) -> List[TagSuggestion]:
        """Generate tag suggestions for a sample based on metadata and audio analysis"""
        suggestions = []

        # 1. BPM-based suggestions
        if sample.bpm:
            bpm_tags = TagService._get_bpm_suggestions(sample.bpm)
            suggestions.extend(bpm_tags)

        # 2. Musical key suggestions
        if sample.key:
            key_tags = TagService._get_key_suggestions(sample.key)
            suggestions.extend(key_tags)

        # 3. TikTok description analysis
        if sample.description:
            desc_tags = TagService._analyze_description(sample.description)
            suggestions.extend(desc_tags)

        # 4. Engagement-based tags
        if sample.view_count or sample.like_count:
            engagement_tags = TagService._get_engagement_tags(
                sample.view_count or 0,
                sample.like_count or 0
            )
            suggestions.extend(engagement_tags)

        # 5. Genre tag if available
        if sample.genre:
            genre_tag = TagSuggestion(
                name=TagService.normalize_tag_name(sample.genre),
                display_name=sample.genre,
                category=TagCategoryEnum.GENRE,
                confidence=0.9,
                reason="Genre metadata from sample"
            )
            suggestions.append(genre_tag)

        # Remove duplicates and sort by confidence
        unique_suggestions = {s.name: s for s in suggestions}
        sorted_suggestions = sorted(
            unique_suggestions.values(),
            key=lambda x: x.confidence,
            reverse=True
        )

        return sorted_suggestions[:15]  # Return top 15 suggestions

    @staticmethod
    def _get_bpm_suggestions(bpm: int) -> List[TagSuggestion]:
        """Generate tags based on BPM"""
        suggestions = []

        if bpm < 90:
            suggestions.append(TagSuggestion(
                name="slow",
                display_name="Slow",
                category=TagCategoryEnum.TEMPO,
                confidence=0.85,
                reason=f"BPM {bpm} is slow tempo"
            ))
            suggestions.append(TagSuggestion(
                name="chill",
                display_name="Chill",
                category=TagCategoryEnum.MOOD,
                confidence=0.7,
                reason="Slow tempo often indicates chill vibe"
            ))
        elif 90 <= bpm < 120:
            suggestions.append(TagSuggestion(
                name="medium",
                display_name="Medium",
                category=TagCategoryEnum.TEMPO,
                confidence=0.85,
                reason=f"BPM {bpm} is medium tempo"
            ))
        elif 120 <= bpm < 140:
            suggestions.append(TagSuggestion(
                name="upbeat",
                display_name="Upbeat",
                category=TagCategoryEnum.TEMPO,
                confidence=0.85,
                reason=f"BPM {bpm} is upbeat"
            ))
            suggestions.append(TagSuggestion(
                name="dance",
                display_name="Dance",
                category=TagCategoryEnum.CONTENT,
                confidence=0.7,
                reason="Upbeat tempo suitable for dance"
            ))
        else:  # >= 140
            suggestions.append(TagSuggestion(
                name="fast",
                display_name="Fast",
                category=TagCategoryEnum.TEMPO,
                confidence=0.85,
                reason=f"BPM {bpm} is fast tempo"
            ))
            suggestions.append(TagSuggestion(
                name="energetic",
                display_name="Energetic",
                category=TagCategoryEnum.MOOD,
                confidence=0.75,
                reason="Fast tempo indicates high energy"
            ))

        # Specific genre suggestions based on BPM ranges
        if 60 <= bpm <= 80:
            suggestions.append(TagSuggestion(
                name="hip-hop",
                display_name="Hip-Hop",
                category=TagCategoryEnum.GENRE,
                confidence=0.6,
                reason="BPM range common in hip-hop"
            ))
        elif 120 <= bpm <= 130:
            suggestions.append(TagSuggestion(
                name="house",
                display_name="House",
                category=TagCategoryEnum.GENRE,
                confidence=0.65,
                reason="BPM range typical of house music"
            ))
        elif 140 <= bpm <= 150:
            suggestions.append(TagSuggestion(
                name="trap",
                display_name="Trap",
                category=TagCategoryEnum.GENRE,
                confidence=0.6,
                reason="BPM range common in trap music"
            ))
        elif bpm >= 170:
            suggestions.append(TagSuggestion(
                name="drum-and-bass",
                display_name="Drum & Bass",
                category=TagCategoryEnum.GENRE,
                confidence=0.65,
                reason="High BPM typical of D&B"
            ))

        return suggestions

    @staticmethod
    def _get_key_suggestions(key: str) -> List[TagSuggestion]:
        """Generate tags based on musical key"""
        suggestions = []

        # Minor keys often sound darker/sadder
        if 'minor' in key.lower() or 'm' in key.lower():
            suggestions.append(TagSuggestion(
                name="dark",
                display_name="Dark",
                category=TagCategoryEnum.MOOD,
                confidence=0.6,
                reason=f"Minor key ({key}) often has darker mood"
            ))

        return suggestions

    @staticmethod
    def _analyze_description(description: str) -> List[TagSuggestion]:
        """Analyze TikTok description for tag suggestions"""
        suggestions = []
        desc_lower = description.lower()

        # Look for keywords in description
        keyword_map = {
            **{k: (v, TagCategoryEnum.GENRE, 0.75) for k, v in TagService.GENRE_TAGS.items()},
            **{k: (v, TagCategoryEnum.MOOD, 0.7) for k, v in TagService.MOOD_TAGS.items()},
            **{k: (v, TagCategoryEnum.INSTRUMENT, 0.7) for k, v in TagService.INSTRUMENT_TAGS.items()},
            **{k: (v, TagCategoryEnum.CONTENT, 0.75) for k, v in TagService.CONTENT_TAGS.items()},
        }

        for keyword, (display, category, confidence) in keyword_map.items():
            if keyword in desc_lower or f"#{keyword.replace(' ', '')}" in desc_lower:
                suggestions.append(TagSuggestion(
                    name=keyword,
                    display_name=display,
                    category=category,
                    confidence=confidence,
                    reason=f"Keyword '{keyword}' found in description"
                ))

        return suggestions

    @staticmethod
    def _get_engagement_tags(views: int, likes: int) -> List[TagSuggestion]:
        """Generate tags based on engagement metrics"""
        suggestions = []

        # High engagement = viral/trending
        if views > 1_000_000:
            suggestions.append(TagSuggestion(
                name="viral",
                display_name="Viral",
                category=TagCategoryEnum.CONTENT,
                confidence=0.85,
                reason=f"{views:,} views indicates viral content"
            ))

        if views > 500_000 or likes > 50_000:
            suggestions.append(TagSuggestion(
                name="trending",
                display_name="Trending",
                category=TagCategoryEnum.CONTENT,
                confidence=0.75,
                reason="High engagement indicates trending content"
            ))

        return suggestions
