// API response types — mirror the backend Pydantic schemas

export interface Job {
  id: number;
  external_id: string;
  source: string;
  title: string;
  company: string;
  location: string | null;
  description: string | null;
  url: string;
  remote: boolean;
  category: string | null;
  tags: string | null; // JSON-encoded array from backend
  published_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface LastRunSummary {
  fetched: number;
  accepted: number;
  duplicates: number;
  rejected: number;
  latency_ms: number | null;
  status: string;
}

export type CircuitBreakerState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';
export type IngestionStatus = 'healthy' | 'degraded' | 'circuit_open' | 'no_data';

export interface IngestionStatusResponse {
  source: string;
  status: IngestionStatus;
  circuit_breaker_state: CircuitBreakerState;
  last_successful_run: string | null;
  last_run_at: string | null;
  jobs_stored: number;
  last_run: LastRunSummary | null;
  data_is_cached: boolean;
  cache_age_seconds: number | null;
}

export type RunStatus =
  | 'SUCCESS'
  | 'WARNING'
  | 'FAILED'
  | 'RATE_LIMITED'
  | 'SCHEMA_ERROR'
  | 'EMPTY_SOURCE'
  | 'CIRCUIT_OPEN'
  | 'TIMEOUT';

export interface IngestionRun {
  id: number;
  source: string;
  started_at: string;
  completed_at: string | null;
  status: RunStatus;
  records_fetched: number;
  records_accepted: number;
  duplicates: number;
  validation_failures: number;
  http_status: number | null;
  latency_ms: number | null;
  error_message: string | null;
}

export interface IngestionTriggerResponse {
  run_id: number;
  status: string;
  message: string;
  records_fetched: number;
  records_accepted: number;
  duplicates: number;
  validation_failures: number;
  latency_ms: number | null;
  error: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  database: 'connected' | 'error';
  source: string;
  last_successful_ingestion: string | null;
  jobs_stored: number;
}

export interface JobFilters {
  search: string;
  remote: '' | 'true' | 'false';
  location: string;
}
