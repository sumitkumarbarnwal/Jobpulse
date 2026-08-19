import { useState } from 'react';
import { EasterEgg } from './components/EasterEgg';
import { IngestionRunsTable } from './components/IngestionRunsTable';
import { JobCard } from './components/JobCard';
import { JobFilters } from './components/JobFilters';
import { MetricCard } from './components/MetricCard';
import { RunIngestionButton } from './components/RunIngestionButton';
import { ScenarioTester } from './components/ScenarioTester';
import { SourceHealth } from './components/SourceHealth';
import { ToastContainer, useToast } from './components/Toast';
import { useIngestionStatus } from './hooks/useIngestionStatus';
import { useJobs } from './hooks/useJobs';
import type { IngestionTriggerResponse, JobFilters as JobFiltersType } from './types';
import { formatRelativeTime, formatSuccessRate } from './utils/format';

// ── Icons ────────────────────────────────────────────────────────────────────
function IconBriefcase() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
    </svg>
  );
}

function IconClock() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  );
}

function IconTrendingUp() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
    </svg>
  );
}

function IconZap() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  );
}

function IconDatabase() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
    </svg>
  );
}

function IconWave() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12 Q5 6 8 12 Q11 18 14 12 Q17 6 20 12 Q22 16 24 12"/>
    </svg>
  );
}

function IconMenu() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  );
}

function IconMoon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  );
}

function IconChevronDown() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  );
}

// Nav icons
function NavIconDashboard() {
  return (
    <svg className="nav-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
      <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>
  );
}

function NavIconJobs() {
  return (
    <svg className="nav-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
    </svg>
  );
}

function NavIconIngestion() {
  return (
    <svg className="nav-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  );
}

function NavIconSources() {
  return (
    <svg className="nav-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
    </svg>
  );
}

function NavIconSettings() {
  return (
    <svg className="nav-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
      <path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
    </svg>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
type NavPage = 'dashboard' | 'jobs' | 'ingestion' | 'sources' | 'settings';

interface SidebarProps {
  activePage: NavPage;
  onPageChange: (page: NavPage) => void;
  sourceName: string;
  sourceHealthy: boolean;
  lastSync: string | null;
  onViewSourceDetails: () => void;
}

function Sidebar({ activePage, onPageChange, sourceName, sourceHealthy, lastSync }: SidebarProps) {
  const navItems: { id: NavPage; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard',  label: 'Dashboard',      icon: <NavIconDashboard /> },
    { id: 'jobs',       label: 'Jobs',            icon: <NavIconJobs /> },
    { id: 'ingestion',  label: 'Ingestion Runs',  icon: <NavIconIngestion /> },
    { id: 'sources',    label: 'Sources',         icon: <NavIconSources /> },
    { id: 'settings',  label: 'Settings',        icon: <NavIconSettings /> },
  ];

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <IconWave />
        </div>
        <span className="sidebar-logo-text">
          Job<span>Pulse</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activePage === item.id ? 'active' : ''}`}
            onClick={() => onPageChange(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Current Source box */}
      <div className="sidebar-bottom">
        <div className="sidebar-source-box">
          <span className="sidebar-source-label">Current Source</span>
          <span className="sidebar-source-name">
            {sourceName.charAt(0).toUpperCase() + sourceName.slice(1)} API
          </span>
          <span className="sidebar-source-status">
            <span className={`status-dot ${sourceHealthy ? 'healthy' : 'degraded'}`} />
            {sourceHealthy ? 'Healthy' : 'Degraded'}
          </span>
          {lastSync && (
            <span className="sidebar-source-sync">
              Last successful ingestion<br />
              {formatRelativeTime(lastSync)}
            </span>
          )}
        </div>

        <span className="sidebar-footer-text">
          Built with{' '}
          <svg width="12" height="12" viewBox="0 0 24 24" fill="#e05d6f" stroke="none">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
          </svg>
          {' '}for engineers
        </span>
      </div>
    </aside>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const { toasts, toast, dismiss } = useToast();
  const { status, runs, loading: statusLoading, error: statusError, refresh: refreshStatus } = useIngestionStatus(15000);
  const { jobs, total, pages, page, loading: jobsLoading, setPage, setFilters, refresh: refreshJobs } = useJobs(20);

  const [filters, setFiltersState] = useState<JobFiltersType>({ search: '', remote: '', location: '' });
  const [activePage, setActivePage] = useState<NavPage>('dashboard');

  const handleFilterChange = (f: JobFiltersType) => {
    setFiltersState(f);
    setFilters(f);
  };

  const handleIngestionComplete = (result: IngestionTriggerResponse) => {
    refreshStatus();
    refreshJobs();
    const st = result.status;
    if (st === 'SUCCESS') {
      toast.success(`Ingestion complete. ${result.records_accepted} new jobs added (${result.duplicates} duplicates).`);
    } else if (st === 'WARNING') {
      toast.warning(`Ingestion finished with warnings. ${result.records_accepted} new jobs, ${result.validation_failures} failures.`);
    } else if (st === 'RATE_LIMITED') {
      toast.warning('Rate limited (429). Exponential backoff triggered. Serving last known good data.');
    } else if (st === 'EMPTY_SOURCE') {
      toast.warning('Empty response [] received. Zero jobs deleted — existing data preserved.');
    } else if (st === 'CIRCUIT_OPEN') {
      toast.error('Circuit breaker is OPEN. Source calls paused to prevent cascading failures.');
    } else {
      toast.error(result.message || 'Ingestion failed. Existing cached data is preserved.');
    }
  };

  const handleIngestionError = (message: string) => toast.error(message);

  // Derived metrics
  const successRateStr = runs.length ? formatSuccessRate(runs) : '—';
  const successRateNum = (() => {
    if (!runs.length) return 0;
    const ok = runs.filter(r => r.status === 'SUCCESS' || r.status === 'WARNING').length;
    return (ok / runs.length) * 100;
  })();
  const latency = status?.last_run?.latency_ms;
  const sourceName = status?.source ?? 'arbeitnow';
  const sourceHealthy = status?.status === 'healthy';
  const lastSyncAgo = status?.last_successful_run
    ? formatRelativeTime(status.last_successful_run)
    : null;

  // Page titles
  const pageTitles: Record<NavPage, { title: string; sub: string }> = {
    dashboard: { title: 'Dashboard', sub: 'Monitor job ingestion, source health, and system performance.' },
    jobs:      { title: 'Jobs',      sub: 'Browse and filter all ingested job listings.' },
    ingestion: { title: 'Ingestion Runs', sub: 'View history and diagnostics for all ingestion runs.' },
    sources:   { title: 'Sources',   sub: 'Configure and monitor your data sources.' },
    settings:  { title: 'Settings',  sub: 'Manage application preferences.' },
  };

  const { title: pageTitle, sub: pageSub } = pageTitles[activePage];

  return (
    <div className="app-shell">
      {/* ── Sidebar ───────────────────────────────────────── */}
      <Sidebar
        activePage={activePage}
        onPageChange={setActivePage}
        sourceName={sourceName}
        sourceHealthy={sourceHealthy}
        lastSync={status?.last_successful_run ?? null}
        onViewSourceDetails={() => setActivePage('sources')}
      />

      {/* ── Main area ─────────────────────────────────────── */}
      <div className="main-area">

        {/* ── Top bar ─────────────────────────────────────── */}
        <header className="topbar">
          <div className="topbar-title">
            <h1>{pageTitle}</h1>
            <p>{pageSub}</p>
          </div>
          <div className="topbar-actions">
            <button className="icon-btn" aria-label="Toggle menu" title="Toggle sidebar">
              <IconMenu />
            </button>
            <RunIngestionButton
              onComplete={handleIngestionComplete}
              onError={handleIngestionError}
            />
            <button className="icon-btn" aria-label="Toggle dark mode" title="Toggle theme">
              <IconMoon />
            </button>
            <button className="avatar-btn" aria-label="User menu">
              <div className="avatar-circle">JP</div>
              <IconChevronDown />
            </button>
          </div>
        </header>

        {/* ── Page content ──────────────────────────────────── */}
        <main className="page-content">

          {/* Error banner */}
          {statusError && (
            <div className="alert-banner alert-banner-error">
              <span>⚠</span>
              Unable to reach the server. Your existing job data is still displayed below.
            </div>
          )}

          {activePage === 'dashboard' && (
            <>
              {/* ── Metric cards row ──────────────────────────── */}
              <div className="metric-cards-row">
                <MetricCard
                  label="Jobs Stored"
                  value={statusLoading ? '' : (status?.jobs_stored?.toLocaleString() ?? '0')}
                  subtext={status?.last_run ? `+${status.last_run.accepted} since last run` : undefined}
                  subtextPositive
                  loading={statusLoading}
                  icon={<IconBriefcase />}
                  iconColor="blue"
                />
                <MetricCard
                  label="Last Successful Run"
                  value={statusLoading ? '' : (lastSyncAgo ?? '—')}
                  subtext={status?.last_successful_run
                    ? new Date(status.last_successful_run).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : undefined}
                  subtextPositive={false}
                  loading={statusLoading}
                  icon={<IconClock />}
                  iconColor="green"
                />
                <MetricCard
                  label="Success Rate"
                  value={statusLoading ? '' : successRateStr}
                  subtext={`Last ${runs.length} runs`}
                  subtextPositive={false}
                  loading={statusLoading}
                  icon={<IconTrendingUp />}
                  iconColor="yellow"
                  progressValue={successRateNum}
                />
                <MetricCard
                  label="API Latency (avg)"
                  value={statusLoading ? '' : (latency != null ? `${latency} ms` : '—')}
                  subtext="Last run"
                  subtextPositive={false}
                  loading={statusLoading}
                  icon={<IconZap />}
                  iconColor="purple"
                />
                <MetricCard
                  label="Source"
                  value={statusLoading ? '' : (sourceName.charAt(0).toUpperCase() + sourceName.slice(1))}
                  subtext="Public Job API"
                  subtextPositive={false}
                  loading={statusLoading}
                  icon={<IconDatabase />}
                  iconColor="cyan"
                />
              </div>

              {/* ── Source Health panel ───────────────────────── */}
              <SourceHealth status={status} loading={statusLoading} runs={runs} />

              {/* ── Scenario Tester (collapsible) ────────────── */}
              <ScenarioTester
                onComplete={handleIngestionComplete}
                onError={handleIngestionError}
              />

              {/* ── Bottom two-column grid ────────────────────── */}
              <div className="dashboard-bottom">

                {/* Left: Recent Ingestion Runs */}
                <div className="surface">
                  <div className="panel-header">
                    <span className="panel-title">Recent Ingestion Runs</span>
                    <button className="panel-link">View all</button>
                  </div>
                  <IngestionRunsTable runs={runs} loading={statusLoading} />
                </div>

                {/* Right: Latest Jobs */}
                <div className="surface" style={{ display: 'flex', flexDirection: 'column' }}>
                  <div className="panel-header">
                    <span className="panel-title">Latest Jobs</span>
                    <button className="panel-link" onClick={() => setActivePage('jobs')}>
                      View all jobs
                    </button>
                  </div>

                  <JobFilters
                    search={filters.search}
                    remote={filters.remote}
                    location={filters.location}
                    onChange={handleFilterChange}
                  />

                  {/* Job list */}
                  {jobsLoading ? (
                    <div style={{ padding: '8px 12px' }}>
                      {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border-muted)' }}>
                          <div className="skeleton" style={{ width: '36px', height: '36px', borderRadius: '8px', flexShrink: 0 }} />
                          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div className="skeleton" style={{ height: '13px', width: '70%' }} />
                            <div className="skeleton" style={{ height: '11px', width: '45%' }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : jobs.length === 0 ? (
                    <div style={{ padding: '32px 24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      {filters.search || filters.remote || filters.location
                        ? 'No jobs match your filters.'
                        : 'No jobs yet. Run an ingestion to populate the database.'}
                    </div>
                  ) : (
                    <>
                      {jobs.slice(0, 8).map((job) => (
                        <JobCard key={job.id} job={job} />
                      ))}
                      <div className="jobs-view-all-footer">
                        <button className="panel-link" onClick={() => setActivePage('jobs')}>
                          View all jobs →
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </>
          )}

          {/* ── Jobs page ─────────────────────────────────────── */}
          {activePage === 'jobs' && (
            <div className="surface">
              <div className="panel-header">
                <span className="panel-title">Jobs</span>
                {!jobsLoading && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {total.toLocaleString()} total
                  </span>
                )}
              </div>

              <JobFilters
                search={filters.search}
                remote={filters.remote}
                location={filters.location}
                onChange={handleFilterChange}
              />

              {jobsLoading ? (
                <div style={{ padding: '8px 12px' }}>
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border-muted)' }}>
                      <div className="skeleton" style={{ width: '36px', height: '36px', borderRadius: '8px', flexShrink: 0 }} />
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div className="skeleton" style={{ height: '13px', width: '60%' }} />
                        <div className="skeleton" style={{ height: '11px', width: '40%' }} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : jobs.length === 0 ? (
                <div style={{ padding: '40px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  {filters.search || filters.remote || filters.location
                    ? 'No jobs match your filters.'
                    : 'No jobs yet. Run an ingestion to populate the database.'}
                </div>
              ) : (
                <>
                  {jobs.map((job) => (
                    <JobCard key={job.id} job={job} />
                  ))}
                  {/* Pagination */}
                  {pages > 1 && (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', padding: '16px', borderTop: '1px solid var(--border-muted)' }}>
                      <button className="btn btn-secondary" id="pagination-prev" disabled={page === 1} onClick={() => setPage(page - 1)}>
                        ← Prev
                      </button>
                      <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                        {page} / {pages}
                      </span>
                      <button className="btn btn-secondary" id="pagination-next" disabled={page === pages} onClick={() => setPage(page + 1)}>
                        Next →
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── Ingestion Runs page ────────────────────────────── */}
          {activePage === 'ingestion' && (
            <div className="surface">
              <div className="panel-header">
                <span className="panel-title">Ingestion Runs</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  Total: {runs.length}
                </span>
              </div>
              <IngestionRunsTable runs={runs} loading={statusLoading} />
            </div>
          )}

          {/* ── Sources page ───────────────────────────────────── */}
          {activePage === 'sources' && (
            <SourceHealth status={status} loading={statusLoading} runs={runs} />
          )}

          {/* ── Settings page ──────────────────────────────────── */}
          {activePage === 'settings' && (
            <div className="surface" style={{ padding: '32px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Settings coming soon.
            </div>
          )}
        </main>

        {/* ── Footer bar ────────────────────────────────────── */}
        <footer className="footer-bar">
          <span>JobPulse v1.0.0</span>
          <span className="footer-dot">•</span>
          <span>Data source: {sourceName.charAt(0).toUpperCase() + sourceName.slice(1)} API</span>
          <span className="footer-dot">•</span>
          <span>Last synced: {lastSyncAgo ?? '—'}</span>
          <span className="footer-dot">•</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span className="footer-status-dot" />
            All systems operational
          </span>
        </footer>
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
      <EasterEgg />
    </div>
  );
}
