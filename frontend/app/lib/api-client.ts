import { ApiError } from '@/types/api';

export class ApiClient {
  private baseUrl: string;
  private getToken?: () => Promise<string | null>;

  constructor(baseUrl: string, getToken?: () => Promise<string | null>) {
    this.baseUrl = baseUrl;
    this.getToken = getToken;
  }

  private async getHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add Authorization header if getToken is provided and returns a token
    if (this.getToken) {
      const token = await this.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP error! status: ${response.status}`,
        status_code: response.status
      }));
      throw new Error(error.detail || 'An error occurred');
    }

    // Handle 204 No Content or empty responses
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return {} as T;
    }

    // Check if response has content
    const text = await response.text();
    if (!text) {
      return {} as T;
    }

    return JSON.parse(text);
  }

  async get<T>(path: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: await this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }

  async post<T>(path: string, body?: any): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  async patch<T>(path: string, body: any): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PATCH',
      headers: await this.getHeaders(),
      body: JSON.stringify(body),
    });

    return this.handleResponse<T>(response);
  }

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: await this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }
}

// Server-side API client for Next.js API routes
// Note: Using NEXT_PUBLIC_API_URL works on both server and client
const getBackendApiUrl = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error('NEXT_PUBLIC_API_URL environment variable is not set. Please configure it in your .env.local file.');
  }
  return `${baseUrl}/api/v1`;
};

export const backendApi = new ApiClient(getBackendApiUrl());

// Helper to create an authenticated API client for use in React components
// Usage: const api = createAuthenticatedClient(getToken);
// Authentication uses Clerk ID from JWT - email not needed
export function createAuthenticatedClient(
  getToken: () => Promise<string | null>
): ApiClient {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error('NEXT_PUBLIC_API_URL environment variable is not set. Please configure it in your .env.local file.');
  }
  return new ApiClient(`${baseUrl}/api/v1`, getToken);
}

// Unauthenticated client for public endpoints (for use in React components)
const getPublicApiUrl = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error('NEXT_PUBLIC_API_URL environment variable is not set. Please configure it in your .env.local file.');
  }
  return `${baseUrl}/api/v1`;
};

export const publicApi = new ApiClient(getPublicApiUrl());