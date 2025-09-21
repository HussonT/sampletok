// API Types matching backend schemas

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
  sort_by?: 'recent' | 'popular' | 'duration';
}

export interface ApiError {
  detail: string;
  status_code?: number;
}