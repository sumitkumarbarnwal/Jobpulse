import type { ReactNode } from 'react';

type IconColor = 'blue' | 'green' | 'yellow' | 'purple' | 'cyan' | 'orange';

interface MetricCardProps {
  label: string;
  value: string | number | ReactNode;
  subtext?: string;
  subtextPositive?: boolean;
  loading?: boolean;
  icon?: ReactNode;
  iconColor?: IconColor;
  progressValue?: number; // 0–100, renders a bar if defined
}

export function MetricCard({
  label,
  value,
  subtext,
  subtextPositive = true,
  loading,
  icon,
  iconColor = 'blue',
  progressValue,
}: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-card-header">
        <span className="metric-card-label">{label}</span>
        {icon && (
          <div className={`metric-icon metric-icon-${iconColor}`}>
            {icon}
          </div>
        )}
      </div>

      {loading ? (
        <div className="skeleton" style={{ height: '32px', width: '80px', borderRadius: '4px' }} />
      ) : (
        <span className="metric-card-value">{value}</span>
      )}

      {progressValue !== undefined && !loading && (
        <div className="metric-progress-bar">
          <div className="metric-progress-fill" style={{ width: `${Math.min(progressValue, 100)}%` }} />
        </div>
      )}

      {loading ? (
        <div className="skeleton" style={{ height: '13px', width: '100px', borderRadius: '4px' }} />
      ) : subtext ? (
        <span className={`metric-card-sub ${subtextPositive ? '' : 'neutral'}`}>
          {subtext}
        </span>
      ) : null}
    </div>
  );
}
