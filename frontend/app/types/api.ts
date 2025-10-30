// API Types matching backend schemas

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
  tags: string[];
  // File URLs - All stored in our infrastructure (R2/S3/GCS)
  audio_url_wav?: string;
  audio_url_mp3?: string;
  waveform_url?: string;
  video_url?: string;  // Our stored video file
  thumbnail_url?: string;  // Our stored thumbnail
  cover_url?: string;  // Our stored cover image
  file_size_video?: number;
  file_size_wav?: number;
  file_size_mp3?: number;
  status: ProcessingStatus;
  error_message?: string;
  created_at: string;
  processed_at?: string;
  download_count?: number;
  tiktok_creator?: TikTokCreator;
  // User-specific fields (only present when authenticated)
  is_favorited?: boolean;
  is_downloaded?: boolean;
  downloaded_at?: string;  // ISO datetime string
  download_type?: string;  // "wav" or "mp3"
  favorited_at?: string;  // ISO datetime string
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
  next_cursor?: string | null; // For cursor-based pagination
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
  sort_by?: 'recent' | 'popular' | 'duration';
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// Collection Types (matching backend)
export interface TikTokCollectionItem {
  id: string;
  name: string;
  state: number;
  video_count: number;
}

export interface TikTokCollectionListResponse {
  collection_list: TikTokCollectionItem[];
  cursor: number;
  hasMore: boolean;
}

export interface ProcessCollectionRequest {
  collection_id: string;
  tiktok_username: string;
  name: string;
  video_count: number;
  cursor?: number;
}

export interface CollectionProcessingTaskResponse {
  collection_id: string;
  status: string;
  message: string;
  credits_deducted: number;
  remaining_credits: number;
  invalid_video_count?: number;
}

export interface CollectionStatusResponse {
  collection_id: string;
  status: string;
  progress: number;
  processed_count: number;
  total_video_count: number;
  message: string;
  error_message?: string;
}

export interface Collection {
  id: string;
  user_id: string;
  tiktok_collection_id: string;
  tiktok_username: string;
  name: string;
  total_video_count: number;
  current_cursor: number;
  next_cursor?: number;
  has_more: boolean;
  status: string;
  processed_count: number;
  sample_count: number;  // Actual number of samples in collection
  cover_image_url?: string;  // Cover image from first sample
  cover_images: string[];  // Array of cover images for cycling display
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CollectionWithSamples extends Collection {
  samples: Sample[];
}