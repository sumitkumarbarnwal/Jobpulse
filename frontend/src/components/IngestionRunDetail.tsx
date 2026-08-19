import { useEffect } from 'react';
import type { IngestionRun } from '../types';
import { formatDateTime, formatDuration, getRunStatusBadgeClass } from '../utils/format';

interface IngestionRunDetailProps {
  run: IngestionRun;
  onClose: () => void;
}

export function IngestionRunDetail({ run, onClose }: IngestionRunDetailProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 50,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backdropFilter: 'blur(3px)',
        padding: '16px',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="modal-content surface"
        style={{
          width: '100%',
          maxWidth: '560px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '0',
          borderRadius: 'var(--radius-xl)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
        }}
        role="dialog"
        aria-modal="true"
        aria-label={`Ingestion Run Detail #${run.id}`}
      >
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'var(--bg-elevated)',
          borderRadius: 'var(--radius-xl) var(--radius-xl) 0 0',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Ingestion Run #{run.id}
            </h3>
            <span className={`badge ${getRunStatusBadgeClass(run.status)}`}>
              {run.status}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', padding: '4px', fontSize: '1.2rem',
              lineHeight: 1,
            }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* Timestamps & Duration */}
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '10px' }}>
              Execution Details
            </div>
            <div className="surface-elevated p-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Started</span>
                <span className="mono" style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                  {formatDateTime(run.started_at)}
                </span>
              </div>
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Completed</span>
                <span className="mono" style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                  {formatDateTime(run.completed_at)}
                </span>
              </div>
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Duration</span>
                <span className="mono" style={{ fontSize: '0.82rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
                  {formatDuration(run.latency_ms)}
                </span>
              </div>
            </div>
          </div>

          {/* Metrics Grid */}
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '10px' }}>
              Ingestion Metrics
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
              <MetricItem label="Fetched" value={run.records_fetched} color="var(--text-primary)" />
              <MetricItem label="New Jobs" value={run.records_accepted} color="var(--accent-green)" />
              <MetricItem label="Duplicates" value={run.duplicates} color="var(--text-secondary)" />
              <MetricItem label="Rejected" value={run.validation_failures} color={run.validation_failures > 0 ? 'var(--accent-red)' : 'var(--text-muted)'} />
            </div>
          </div>

          {/* Technical Info */}
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '10px' }}>
              Technical Breakdown
            </div>
            <div className="surface-elevated p-3" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>HTTP Status</span>
                <span className="mono" style={{ color: run.http_status === 200 ? 'var(--accent-green)' : run.http_status ? 'var(--accent-yellow)' : 'var(--text-muted)', fontWeight: 600 }}>
                  {run.http_status ?? 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Source</span>
                <span className="mono" style={{ color: 'var(--text-primary)' }}>
                  {run.source.charAt(0).toUpperCase() + run.source.slice(1)}
                </span>
              </div>
            </div>
          </div>

          {/* Error Details if any */}
          {run.error_message && (
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--accent-red)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '8px' }}>
                Error Diagnostic Log
              </div>
              <div style={{
                background: 'var(--accent-red-muted)',
                border: '1px solid rgba(248,81,73,0.3)',
                borderRadius: 'var(--radius-md)',
                padding: '12px',
                color: 'var(--accent-red)',
                fontSize: '0.8rem',
                fontFamily: 'var(--font-mono)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                lineHeight: 1.5,
              }}>
                {run.error_message}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricItem({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="surface-elevated p-3" style={{ textAlign: 'center' }}>
      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
        {label}
      </span>
      <span className="mono" style={{ fontSize: '1.2rem', fontWeight: 700, color }}>
        {value}
      </span>
    </div>
  );
}
