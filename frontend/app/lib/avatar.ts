/**
 * Avatar utilities using DiceBear for fallback avatars
 */
import { createAvatar } from '@dicebear/core';
import { notionists, funEmoji } from '@dicebear/collection';

export type AvatarStyle = 'notionists' | 'fun-emoji';

/**
 * Generate a deterministic avatar URL based on seed (username, ID, etc.)
 *
 * @param seed - Unique identifier (username, user ID, etc.)
 * @param style - Avatar style to use (default: 'notionists')
 * @returns Data URI of the generated SVG avatar
 */
export function generateAvatarUrl(seed: string, style: AvatarStyle = 'notionists'): string {
  if (style === 'fun-emoji') {
    const avatar = createAvatar(funEmoji, { seed });
    return avatar.toDataUri();
  }

  const avatar = createAvatar(notionists, {
    seed,
    backgroundColor: ['b6e3f4', 'c0aede', 'd1d4f9', 'ffd5dc', 'ffdfbf'],
  });

  return avatar.toDataUri();
}

/**
 * Get avatar URL with fallback to generated avatar
 *
 * @param avatarUrl - Optional avatar URL from storage
 * @param seed - Seed for generating fallback avatar
 * @param style - Avatar style for fallback
 * @returns Avatar URL or generated data URI
 */
export function getAvatarWithFallback(
  avatarUrl: string | undefined | null,
  seed: string,
  style: AvatarStyle = 'notionists'
): string {
  if (avatarUrl) {
    return avatarUrl;
  }
  return generateAvatarUrl(seed, style);
}
