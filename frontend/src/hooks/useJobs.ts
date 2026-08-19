import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchJobs } from '../services/api';
import type { Job, JobFilters, JobListResponse } from '../types';

interface UseJobsResult {
  jobs: Job[];
  total: number;
  pages: number;
  page: number;
  loading: boolean;
  error: string | null;
  setPage: (page: number) => void;
  setFilters: (filters: Partial<JobFilters>) => void;
  refresh: () => void;
}

export function useJobs(limit: number = 20): UseJobsResult {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFiltersState] = useState<Partial<JobFilters>>({});
  const abortRef = useRef<AbortController | null>(null);

  const fetch = useCallback(
    async (currentPage: number, currentFilters: Partial<JobFilters>) => {
      // Cancel previous in-flight request
      if (abortRef.current) abortRef.current.abort();
      abortRef.current = new AbortController();

      setLoading(true);
      try {
        const data: JobListResponse = await fetchJobs({
          page: currentPage,
          limit,
          ...currentFilters,
        });
        setJobs(data.jobs);
        setTotal(data.total);
        setPages(data.pages);
        setError(null);
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError(
            err instanceof Error ? err.message : 'Failed to load jobs',
          );
        }
      } finally {
        setLoading(false);
      }
    },
    [limit],
  );

  useEffect(() => {
    fetch(page, filters);
  }, [fetch, page, filters]);

  const setFilters = useCallback((newFilters: Partial<JobFilters>) => {
    setPage(1);
    setFiltersState(newFilters);
  }, []);

  return {
    jobs,
    total,
    pages,
    page,
    loading,
    error,
    setPage,
    setFilters,
    refresh: () => fetch(page, filters),
  };
}
