/**
 * Extract hashtags from text
 */
export function extractHashtags(text: string): string[] {
  if (!text) return [];

  const hashtagPattern = /#(\w+)/g;
  const hashtags = Array.from(text.matchAll(hashtagPattern), (m) => m[1].toLowerCase());

  // Remove duplicates while preserving order
  return Array.from(new Set(hashtags));
}

/**
 * Remove hashtags from text
 */
export function removeHashtags(text: string): string {
  if (!text) return text;

  // Remove hashtags and clean up extra spaces
  const textWithoutHashtags = text.replace(/#\w+/g, '');
  // Clean up multiple spaces and trim
  return textWithoutHashtags.replace(/\s+/g, ' ').trim();
}
