"""
Text processing utilities
"""
import re
from typing import List


# Tags to filter out (common spam/low-value tags)
FILTERED_TAGS = {
    'fyp', 'foryou', 'foryoupage', 'viral', 'viralvideo',
    'trending', 'tiktok', 'fy'
}


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text, filtering out common spam tags.

    Args:
        text: Text containing hashtags (e.g., "#beyonce #acoustic #fyp")

    Returns:
        List of hashtags without the # symbol, lowercased
        Example: ["beyonce", "acoustic"]
    """
    if not text:
        return []

    # Match hashtags: # followed by word characters (letters, numbers, underscores)
    hashtag_pattern = r'#(\w+)'
    hashtags = re.findall(hashtag_pattern, text)

    # Convert to lowercase and remove duplicates while preserving order
    seen = set()
    unique_hashtags = []
    for tag in hashtags:
        tag_lower = tag.lower()

        # Skip if already seen
        if tag_lower in seen:
            continue

        # Skip if it's a filtered tag
        if tag_lower in FILTERED_TAGS:
            continue

        # Skip if it starts with 'fyp' followed by special characters (e.g., fypシ, fyppppp...)
        if tag_lower.startswith('fyp') and (len(tag_lower) > 3 or not tag_lower.isalpha()):
            continue

        seen.add(tag_lower)
        unique_hashtags.append(tag_lower)

    return unique_hashtags


def remove_hashtags(text: str) -> str:
    """
    Remove hashtags from text.

    Args:
        text: Text containing hashtags (e.g., "literally my fave song #Halo #beyonce")

    Returns:
        Text with hashtags removed and cleaned up
        Example: "literally my fave song"
    """
    if not text:
        return text

    # Remove hashtags and clean up extra spaces
    text_without_hashtags = re.sub(r'#\w+', '', text)
    # Clean up multiple spaces and strip
    text_cleaned = re.sub(r'\s+', ' ', text_without_hashtags).strip()

    return text_cleaned
