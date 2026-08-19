import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchIngestionRuns, fetchIngestionStatus } from '../services/api';
import type { IngestionRun, IngestionStatusResponse } from '../types';

interface UseIngestionStatusResult {
  status: IngestionStatusResponse | null;
  runs: IngestionRun[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Polls ingestion status and recent runs on a configurable interval.
 *
 * Polling is paused when the document is hidden (tab not visible) to
 * avoid unnecessary requests. Resumes when the tab becomes active again.
 */
export function useIngestionStatus(
  intervalMs: number = 15_000,
): UseIngestionStatusResult {
  const [status, setStatus] = useState<IngestionStatusResponse | null>(null);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetch = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([
        fetchIngestionStatus(),
        fetchIngestionRuns(10),
      ]);
      setStatus(s);
      setRuns(r);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();

    const schedule = () => {
      timerRef.current = setTimeout(() => {
        if (!document.hidden) {
          fetch();
        }
        schedule();
      }, intervalMs);
    };

    schedule();

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetch();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetch, intervalMs]);

  return { status, runs, loading, error, refresh: fetch };
}
