import { useState } from 'react';
import type { IngestionRun } from '../types';
import { formatDuration, formatRelativeTime, getRunStatusBadgeClass } from '../utils/format';
import { IngestionRunDetail } from './IngestionRunDetail';

interface IngestionRunsTableProps {
  runs: IngestionRun[];
  loading: boolean;
}

export function IngestionRunsTable({ runs, loading }: IngestionRunsTableProps) {
  const [selectedRun, setSelectedRun] = useState<IngestionRun | null>(null);

  if (loading) {
    return (
      <div style={{ padding: '12px' }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton" style={{ height: '34px', borderRadius: '4px', marginBottom: '4px' }} />
        ))}
      </div>
    );
  }

  if (!runs.length) {
    return (
      <div style={{ textAlign: 'center', padding: '28px 24px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No ingestion runs yet.{' '}
        <strong style={{ color: 'var(--text-secondary)' }}>Run Ingestion</strong> to start.
      </div>
    );
  }

  return (
    <>
      <div style={{ overflowX: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>Started At</th>
              <th>Status</th>
              <th>Fetched</th>
              <th>Accepted</th>
              <th>Duplicates</th>
              <th>Rejected</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr
                key={run.id}
                onClick={() => setSelectedRun(run)}
                title="Click to view full run metrics & diagnostics"
              >
                <td className="mono" style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>
                  {formatRelativeTime(run.completed_at || run.started_at)}
                </td>
                <td>
                  <span className={`badge ${getRunStatusBadgeClass(run.status)}`}>{run.status}</span>
                </td>
                <td className="mono">{run.records_fetched}</td>
                <td className="mono" style={{ color: run.records_accepted > 0 ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                  {run.records_accepted}
                </td>
                <td className="mono" style={{ color: run.duplicates > 0 ? 'var(--text-secondary)' : 'var(--text-muted)' }}>
                  {run.duplicates}
                </td>
                <td className="mono" style={{ color: run.validation_failures > 0 ? 'var(--accent-yellow)' : 'var(--text-muted)' }}>
                  {run.validation_failures}
                </td>
                <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                  {formatDuration(run.latency_ms)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <button className="table-footer-link">
          View all runs →
        </button>
      </div>

      {selectedRun && (
        <IngestionRunDetail run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
    </>
  );
}
