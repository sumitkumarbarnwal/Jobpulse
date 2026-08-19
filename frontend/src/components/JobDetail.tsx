import { useEffect } from 'react';
import type { Job } from '../types';
import { formatDateTime, formatRelativeTime, parseTags } from '../utils/format';

interface JobDetailProps {
  job: Job;
  onClose: () => void;
}

function MetaItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '3px', fontWeight: 600 }}>
        {label}
      </div>
      <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontFamily: mono ? 'var(--font-mono)' : undefined }}>
        {value}
      </div>
    </div>
  );
}

// Strip trailing junk that Arbeitnow appends (e.g. "Find [Jobs in X] on Arbeitnow")
function cleanDescription(html: string): string {
  // Remove the trailing "Find [Jobs in ...] on Arbeitnow" markdown link that
  // gets appended by the source and bleeds into the rendered HTML.
  return html.replace(/Find\s+\[.*?\]\(https?:\/\/[^)]*\)\s+on\s+\w+/gi, '').trim();
}

export function JobDetail({ job, onClose }: JobDetailProps) {
  const tags = parseTags(job.tags);

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

  const descriptionHtml = job.description ? cleanDescription(job.description) : null;

  return (
    /* ── Backdrop ──────────────────────────────────────────── */
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backdropFilter: 'blur(4px)',
        padding: '24px 16px',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* ── Modal panel ─────────────────────────────────────── */}
      <div
        className="modal-content"
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-xl)',
          width: '100%',
          maxWidth: '760px',
          maxHeight: '88vh',
          overflowY: 'auto',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
        }}
        role="dialog"
        aria-modal="true"
        aria-label={`Job detail: ${job.title}`}
      >
        {/* ── Sticky header ─────────────────────────────────── */}
        <div style={{
          padding: '20px 24px 16px',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: '16px',
          position: 'sticky',
          top: 0,
          background: 'var(--bg-surface)',
          zIndex: 1,
          borderRadius: 'var(--radius-xl) var(--radius-xl) 0 0',
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>
              {job.title}
            </h2>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {job.company}
              {job.location && <span style={{ color: 'var(--text-muted)' }}> · {job.location}</span>}
            </div>
          </div>
          <button
            onClick={onClose}
            id="job-detail-close"
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '4px 8px',
              fontSize: '1rem',
              lineHeight: 1.5,
              flexShrink: 0,
              transition: 'background 120ms ease',
            }}
            aria-label="Close"
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
          >
            ✕
          </button>
        </div>

        {/* ── Badges ────────────────────────────────────────── */}
        {(job.remote || job.category || tags.length > 0) && (
          <div style={{
            padding: '12px 24px',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px',
            borderBottom: '1px solid var(--border-muted)',
          }}>
            {job.remote && <span className="remote-badge">Remote</span>}
            {job.category && <span className="tag">{job.category}</span>}
            {tags.map((tag) => (
              <span key={tag} className="tag">{tag}</span>
            ))}
          </div>
        )}

        {/* ── Body ──────────────────────────────────────────── */}
        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '20px', flex: 1 }}>

          {/* Description */}
          {descriptionHtml && (
            <div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '12px', fontWeight: 600 }}>
                Description
              </div>
              <div
                className="job-description-body"
                dangerouslySetInnerHTML={{ __html: descriptionHtml }}
              />
            </div>
          )}

          {/* Meta grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: '12px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border-muted)',
          }}>
            <MetaItem label="Source"     value={job.source} mono />
            <MetaItem label="Published"  value={job.published_at ? formatDateTime(job.published_at) : '—'} />
            <MetaItem label="First Seen" value={formatRelativeTime(job.first_seen_at)} />
            <MetaItem label="Last Seen"  value={formatRelativeTime(job.last_seen_at)} />
          </div>

          {/* CTA */}
          <div style={{ paddingTop: '4px', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              id={`job-detail-link-${job.id}`}
              className="btn btn-primary"
              style={{ textDecoration: 'none' }}
            >
              View original listing →
            </a>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: 0 }}>
              Data source: {job.source.charAt(0).toUpperCase() + job.source.slice(1)} · External link opens in new tab
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
