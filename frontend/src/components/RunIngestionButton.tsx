import { useState } from 'react';
import { triggerIngestion } from '../services/api';
import type { IngestionTriggerResponse } from '../types';

interface RunIngestionButtonProps {
  onComplete: (result: IngestionTriggerResponse) => void;
  onError: (message: string) => void;
}

type ButtonState = 'idle' | 'running' | 'success' | 'error';

export function RunIngestionButton({ onComplete, onError }: RunIngestionButtonProps) {
  const [state, setState] = useState<ButtonState>('idle');

  const handleClick = async () => {
    if (state === 'running') return;

    setState('running');
    try {
      const result = await triggerIngestion();
      setState(result.status === 'FAILED' ? 'error' : 'success');
      onComplete(result);

      // Reset button to idle after 3s
      setTimeout(() => setState('idle'), 3000);
    } catch (err) {
      setState('error');
      onError(err instanceof Error ? err.message : 'Ingestion failed');
      setTimeout(() => setState('idle'), 3000);
    }
  };

  const labels: Record<ButtonState, string> = {
    idle: 'Run Ingestion',
    running: 'Running...',
    success: 'Done ✓',
    error: 'Failed ✗',
  };

  const styles: Record<ButtonState, React.CSSProperties> = {
    idle: {},
    running: { opacity: 0.8 },
    success: { background: 'var(--accent-green)', border: '1px solid transparent' },
    error: { background: 'var(--accent-red-muted)', color: 'var(--accent-red)', border: '1px solid rgba(248,81,73,0.4)' },
  };

  return (
    <button
      id="run-ingestion-btn"
      className="btn btn-primary"
      onClick={handleClick}
      disabled={state === 'running'}
      style={{ ...styles[state], minWidth: '130px', justifyContent: 'center' }}
      aria-label={state === 'running' ? 'Ingestion in progress' : 'Run ingestion'}
    >
      {state === 'running' && (
        <svg
          width="14" height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="spinner"
          aria-hidden="true"
        >
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
      )}
      {labels[state]}
    </button>
  );
}
