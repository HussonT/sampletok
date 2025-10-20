// API Types matching backend schemas

export enum TagCategory {
  GENRE = 'genre',
  MOOD = 'mood',
  INSTRUMENT = 'instrument',
  CONTENT = 'content',
  TEMPO = 'tempo',
  EFFECT = 'effect',
  OTHER = 'other'
}

export interface Tag {
  id: string;
  name: string;
  display_name: string;
  category: TagCategory;
  usage_count: number;
  created_at: string;
}

export interface TagSuggestion {
  name: string;
  display_name: string;
  category: TagCategory;
  confidence: number;
  reason: string;
}

export interface TagSuggestionsResponse {
  suggestions: TagSuggestion[];
  sample_id: string;
}

export interface AddTagsRequest {
  tag_names: string[];
}

export interface PopularTagsResponse {
  tags: Tag[];
  total: number;
}

export interface TikTokCreator {
  id: string;
  tiktok_id: string;
  username: string;
  nickname?: string;
  avatar_thumb?: string;
  avatar_medium?: string;
  avatar_large?: string;
  signature?: string;
  verified: boolean;
  follower_count: number;
  following_count: number;
  heart_count: number;
  video_count: number;
}

export interface Sample {
  id: string;
  tiktok_url?: string;
  tiktok_id?: string;
  aweme_id?: string;
  title?: string;
  region?: string;
  creator_username?: string;
  creator_name?: string;
  creator_avatar_url?: string;
  creator_follower_count?: number;
  description?: string;
  view_count: number;
  like_count: number;
  share_count: number;
  comment_count: number;
  upload_timestamp?: number;
  duration_seconds?: number;
  bpm?: number;
  key?: string;
  genre?: string;
  tags: string[]; // Legacy field
  tag_objects: Tag[]; // New structured tags
  audio_url_wav?: string;
  audio_url_mp3?: string;
  waveform_url?: string;
  thumbnail_url?: string;
  origin_cover_url?: string;
  music_url?: string;
  video_url?: string;
  video_url_watermark?: string;
  status: ProcessingStatus;
  error_message?: string;
  created_at: string;
  processed_at?: string;
  tiktok_creator?: TikTokCreator;
}

export enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface ProcessingTaskResponse {
  task_id: string;
  status: string;
  message: string;
  sample_id?: string;
}

export interface ProcessingStatusResponse {
  status: ProcessingStatus;
  progress?: number;
  message?: string;
  sample_id?: string;
  error?: string;
}

export interface TikTokURLInput {
  url: string;
}

export interface SampleUpdate {
  description?: string;
  genre?: string;
  tags?: string[];
}

export interface SampleFilters {
  skip?: number;
  limit?: number;
  genre?: string;
  status?: string;
  search?: string;
  tags?: string; // Comma-separated tag names
  sort_by?: 'recent' | 'popular' | 'duration';
}

export interface ApiError {
  detail: string;
  status_code?: number;
}