import type {
  HealthResponse,
  IngestionRun,
  IngestionStatusResponse,
  IngestionTriggerResponse,
  Job,
  JobFilters,
  JobListResponse,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL ?? '';

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
  name: 'ApiError';
}

function makeApiError(status: number, message: string, detail?: unknown): ApiError {
  return { status, message, detail, name: 'ApiError' };
}

export function isApiError(err: unknown): err is ApiError {
  return typeof err === 'object' && err !== null && (err as ApiError).name === 'ApiError';
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  let response: Response;

  try {
    response = await fetch(url, {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      ...options,
    });
  } catch (_err) {
    throw makeApiError(0, 'Unable to reach the server. Check your connection.');
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = null;
    }

    const message =
      response.status === 409
        ? 'An ingestion run is already in progress.'
        : response.status === 429
          ? 'Too many requests. Please wait before trying again.'
          : response.status >= 500
            ? 'The server encountered an error. Your existing data is still available.'
            : `Request failed (${response.status})`;

    throw makeApiError(response.status, message, detail);
  }

  return response.json() as Promise<T>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Jobs
// ─────────────────────────────────────────────────────────────────────────────

export function fetchJobs(
  filters: Partial<JobFilters> & { page?: number; limit?: number },
): Promise<JobListResponse> {
  const params = new URLSearchParams();
  if (filters.page) params.set('page', String(filters.page));
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.search) params.set('search', filters.search);
  if (filters.remote) params.set('remote', filters.remote);
  if (filters.location) params.set('location', filters.location);
  const qs = params.toString();
  return request<JobListResponse>(`/api/jobs${qs ? `?${qs}` : ''}`);
}

export function fetchJob(id: number): Promise<Job> {
  return request<Job>(`/api/jobs/${id}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Ingestion
// ─────────────────────────────────────────────────────────────────────────────

export function fetchIngestionStatus(): Promise<IngestionStatusResponse> {
  return request<IngestionStatusResponse>('/api/ingestion/status');
}

export function fetchIngestionRuns(limit = 20): Promise<IngestionRun[]> {
  return request<IngestionRun[]>(`/api/ingestion/runs?limit=${limit}`);
}

export function triggerIngestion(
  source?: string,
  scenario?: string,
): Promise<IngestionTriggerResponse> {
  const params = new URLSearchParams();
  if (source) params.set('source', source);
  if (scenario) params.set('scenario', scenario);
  const qs = params.toString();
  return request<IngestionTriggerResponse>(`/api/ingestion/run${qs ? `?${qs}` : ''}`, { method: 'POST' });
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export { makeApiError as createApiError };
