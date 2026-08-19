/**
 * Formatting utilities used across components.
 */

export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return 'Never';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);

    if (diffSeconds < 5) return 'just now';
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return 'Unknown';
  }
}

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    return new Date(isoString).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '—';
  }
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function parseTags(tagsJson: string | null | undefined): string[] {
  if (!tagsJson) return [];
  try {
    const parsed = JSON.parse(tagsJson);
    if (Array.isArray(parsed)) return parsed.map(String);
    return [];
  } catch {
    return [];
  }
}

export function getRunStatusBadgeClass(status: string): string {
  switch (status) {
    case 'SUCCESS': return 'badge-success';
    case 'WARNING': return 'badge-warning';
    case 'FAILED':
    case 'SCHEMA_ERROR':
    case 'TIMEOUT': return 'badge-error';
    case 'RATE_LIMITED': return 'badge-warning';
    case 'CIRCUIT_OPEN': return 'badge-neutral';
    case 'EMPTY_SOURCE': return 'badge-warning';
    default: return 'badge-neutral';
  }
}

export function formatSuccessRate(runs: { status: string }[]): string {
  if (!runs.length) return '—';
  const successes = runs.filter(r => r.status === 'SUCCESS' || r.status === 'WARNING').length;
  return `${((successes / runs.length) * 100).toFixed(1)}%`;
}
