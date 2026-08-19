import { useState } from 'react';
import type { Job } from '../types';
import { formatRelativeTime } from '../utils/format';
import { JobDetail } from './JobDetail';

interface JobCardProps {
  job: Job;
}

// Generate a consistent background color from a company name
function companyColor(name: string): string {
  const colors = [
    '#1a8cff', '#e85d04', '#7b2d8b', '#00897b', '#c62828',
    '#1565c0', '#6a1b9a', '#00695c', '#ad1457', '#f57c00',
    '#2e7d32', '#0277bd', '#4527a0', '#283593', '#558b2f',
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function CompanyAvatar({ company }: { company: string }) {
  const initials = company
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
  const bg = companyColor(company);

  return (
    <div
      className="job-company-avatar"
      style={{ background: bg }}
      aria-label={company}
    >
      {initials}
    </div>
  );
}

export function JobCard({ job }: JobCardProps) {
  const [showDetail, setShowDetail] = useState(false);

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        id={`job-card-${job.id}`}
        className="job-list-item"
        onClick={() => setShowDetail(true)}
        onKeyDown={(e) => e.key === 'Enter' && setShowDetail(true)}
      >
        <CompanyAvatar company={job.company} />

        <div className="job-list-info">
          <div className="job-list-title">{job.title}</div>
          <div className="job-list-meta">
            <span style={{ color: 'var(--text-secondary)' }}>{job.company}</span>
            {job.remote && (
              <span className="remote-badge">Remote</span>
            )}
            {!job.remote && job.location && (
              <>
                <span style={{ color: 'var(--border-default)' }}>·</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                  📍 {job.location}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="job-list-right">
          <span className="job-list-time">
            {formatRelativeTime(job.published_at || job.first_seen_at)}
          </span>
          <span className="job-source-tag">{job.source}</span>
        </div>

        <svg
          className="job-list-chevron"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </div>

      {showDetail && (
        <JobDetail job={job} onClose={() => setShowDetail(false)} />
      )}
    </>
  );
}
