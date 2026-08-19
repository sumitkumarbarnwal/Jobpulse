import type { CircuitBreakerState, IngestionRun, IngestionStatus, IngestionStatusResponse } from '../types';
import { formatRelativeTime } from '../utils/format';

interface SourceHealthProps {
  status: IngestionStatusResponse | null;
  loading: boolean;
  runs?: IngestionRun[];
}

function getDotClass(status: IngestionStatus, cb: CircuitBreakerState): string {
  if (cb === 'OPEN') return 'open';
  if (cb === 'HALF_OPEN') return 'degraded';
  if (status === 'healthy') return 'healthy';
  if (status === 'degraded') return 'degraded';
  return 'no-data';
}

function getStatusLabel(status: IngestionStatus, cb: CircuitBreakerState): string {
  if (cb === 'OPEN') return 'Circuit Open';
  if (cb === 'HALF_OPEN') return 'Probing';
  if (status === 'healthy') return 'Healthy';
  if (status === 'degraded') return 'Degraded';
  if (status === 'no_data') return 'No Data';
  return 'Unknown';
}

function getCbClass(state: CircuitBreakerState): string {
  if (state === 'CLOSED') return 'cb-closed';
  if (state === 'OPEN') return 'cb-open';
  return 'cb-halfopen';
}

// Build sparkline SVG path from run array
function buildSparklinePath(runs: IngestionRun[], w: number, h: number): { area: string; line: string } {
  if (!runs.length) return { area: '', line: '' };

  // Collect success rates per run (1 = success, 0 = fail)
  const points = [...runs].reverse().map((r) =>
    r.status === 'SUCCESS' || r.status === 'WARNING' ? 100 : 0
  );

  // Smooth with a running average (window = 3)
  const smoothed = points.map((_, i) => {
    const slice = points.slice(Math.max(0, i - 2), i + 1);
    return slice.reduce((a, b) => (a as number) + b, 0) / slice.length;
  });

  const minV = 0;
  const maxV = 100;
  const range = maxV - minV || 1;
  const n = smoothed.length;
  const stepX = w / Math.max(n - 1, 1);

  const pts = smoothed.map((v, i) => ({
    x: i * stepX,
    y: h - ((v - minV) / range) * h,
  }));

  // Build smooth bezier path
  const lineParts: string[] = [];
  const areaParts: string[] = [`M ${pts[0].x} ${h}`];

  pts.forEach((pt, i) => {
    if (i === 0) {
      lineParts.push(`M ${pt.x} ${pt.y}`);
      areaParts.push(`L ${pt.x} ${pt.y}`);
    } else {
      const prev = pts[i - 1];
      const cpX = (prev.x + pt.x) / 2;
      lineParts.push(`C ${cpX} ${prev.y} ${cpX} ${pt.y} ${pt.x} ${pt.y}`);
      areaParts.push(`C ${cpX} ${prev.y} ${cpX} ${pt.y} ${pt.x} ${pt.y}`);
    }
  });

  const last = pts[pts.length - 1];
  areaParts.push(`L ${last.x} ${h} Z`);

  return { line: lineParts.join(' '), area: areaParts.join(' ') };
}

function SuccessRateSparkline({ runs }: { runs: IngestionRun[] }) {
  const W = 200;
  const H = 60;
  const { line, area } = buildSparklinePath(runs, W, H);

  return (
    <div className="sparkline-container">
      <div className="sparkline-header">
        <span className="sparkline-title">Ingestion Success Rate (Last {runs.length} Runs)</span>
      </div>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'stretch' }}>
        {/* Y axis labels */}
        <div className="sparkline-y-labels" style={{ position: 'static', width: '28px', flexShrink: 0 }}>
          <span>100%</span>
          <span>50%</span>
          <span>0%</span>
        </div>
        <div style={{ flex: 1, position: 'relative' }}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="sparkline-svg"
            preserveAspectRatio="none"
            style={{ height: '60px' }}
          >
            <defs>
              <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3fb950" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#3fb950" stopOpacity="0.02" />
              </linearGradient>
            </defs>
            {/* Grid lines */}
            <line x1="0" y1={H * 0.5} x2={W} y2={H * 0.5} stroke="#30363d" strokeWidth="0.5" strokeDasharray="3 3" />
            {/* Area fill */}
            {area && <path d={area} fill="url(#sparkGrad)" />}
            {/* Line */}
            {line && <path d={line} fill="none" stroke="#3fb950" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />}
          </svg>
          <div className="sparkline-x-labels" style={{ marginTop: '2px' }}>
            <span>{runs.length} runs ago</span>
            <span>Now</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function SourceHealth({ status, loading, runs = [] }: SourceHealthProps) {
  if (loading) {
    return (
      <div className="source-health-card">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div className="skeleton" style={{ height: '14px', width: '80px' }} />
          <div className="skeleton" style={{ height: '22px', width: '120px' }} />
          <div className="skeleton" style={{ height: '12px', width: '90px' }} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div className="skeleton" style={{ height: '11px', width: '90px' }} />
              <div className="skeleton" style={{ height: '17px', width: '60px' }} />
            </div>
          ))}
        </div>
        <div />
        <div className="skeleton" style={{ height: '80px', borderRadius: '6px' }} />
      </div>
    );
  }

  if (!status) return null;

  const dotClass = getDotClass(status.status, status.circuit_breaker_state);
  const statusLabel = getStatusLabel(status.status, status.circuit_breaker_state);
  const cbClass = getCbClass(status.circuit_breaker_state);
  const latency = status.last_run?.latency_ms;
  const sourceDisplayName = status.source.charAt(0).toUpperCase() + status.source.slice(1) + ' API';

  // Error rate from runs
  const errorRateStr = (() => {
    if (!runs.length) return '—';
    const failures = runs.filter(r => r.status === 'FAILED' || r.status === 'CIRCUIT_OPEN' || r.status === 'TIMEOUT').length;
    return `${((failures / runs.length) * 100).toFixed(1)}%`;
  })();

  const isUnavailable = status.circuit_breaker_state === 'OPEN' || status.status === 'degraded' || status.data_is_cached;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div className="source-health-card">
        {/* ── Status block ─────────────────────────── */}
        <div className="source-health-status">
          <span className="source-health-title">Source Health</span>
          <div className="source-health-status-label">
            <span className={`status-dot ${dotClass}`} />
            <span className="source-health-status-name" style={{
              color: dotClass === 'healthy' ? 'var(--accent-green)' :
                     dotClass === 'open' ? 'var(--accent-red)' :
                     dotClass === 'degraded' ? 'var(--accent-yellow)' : 'var(--text-muted)'
            }}>
              {statusLabel}
            </span>
          </div>
          <span className="source-health-api-name">{sourceDisplayName}</span>
          <span className={`cb-badge ${cbClass}`}>
            CIRCUIT {status.circuit_breaker_state}
          </span>
        </div>

        {/* ── KPI grid ─────────────────────────────── */}
        <div className="source-health-kpis">
          <div className="source-kpi">
            <div className="source-kpi-icon-row">
              <svg className="source-kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
              <span className="source-kpi-label">Last Successful Ingestion</span>
            </div>
            <span className="source-kpi-value">
              {status.last_successful_run ? formatRelativeTime(status.last_successful_run) : '—'}
            </span>
          </div>

          <div className="source-kpi">
            <div className="source-kpi-icon-row">
              <svg className="source-kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              <span className="source-kpi-label">API Latency (Last Run)</span>
            </div>
            <span className="source-kpi-value">
              {latency != null ? `${latency} ms` : '—'}
            </span>
          </div>

          <div className="source-kpi">
            <div className="source-kpi-icon-row">
              <svg className="source-kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
              </svg>
              <span className="source-kpi-label">Records Fetched (Last Run)</span>
            </div>
            <span className="source-kpi-value">
              {status.last_run?.fetched ?? '—'}
            </span>
          </div>

          <div className="source-kpi">
            <div className="source-kpi-icon-row">
              <svg className="source-kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <span className="source-kpi-label">Error Rate (Last {runs.length} Runs)</span>
            </div>
            <span className="source-kpi-value" style={{ color: errorRateStr !== '0.0%' && errorRateStr !== '—' ? 'var(--accent-yellow)' : undefined }}>
              {errorRateStr}
            </span>
          </div>
        </div>

        {/* ── Divider column ───────────────────────── */}
        <div style={{ borderLeft: '1px solid var(--border-muted)', margin: '0 4px' }} />

        {/* ── Sparkline ────────────────────────────── */}
        {runs.length > 1 ? (
          <SuccessRateSparkline runs={runs} />
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            Run at least 2 ingestions to see chart
          </div>
        )}
      </div>

      {/* ── Warning banner ──────────────────────────── */}
      {isUnavailable && (
        <div className={`alert-banner ${status.circuit_breaker_state === 'OPEN' ? 'alert-banner-error' : 'alert-banner-warning'}`}>
          <span style={{ fontSize: '1rem', flexShrink: 0 }}>⚠</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>
              {status.last_run?.status === 'EMPTY_SOURCE'
                ? 'EMPTY SOURCE RESPONSE RECEIVED'
                : status.circuit_breaker_state === 'OPEN'
                ? 'SOURCE UNAVAILABLE — CIRCUIT BREAKER OPEN'
                : 'SOURCE DEGRADED — SERVING CACHED DATA'}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {status.circuit_breaker_state === 'OPEN'
                ? `${sourceDisplayName} isn't responding (repeated failures). Circuit breaker is OPEN to prevent cascading failures.`
                : `${sourceDisplayName} encountered an issue during the last ingestion. Showing ${status.jobs_stored.toLocaleString()} cached jobs.`}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
