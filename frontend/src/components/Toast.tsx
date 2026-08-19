import { useState } from 'react';

type ToastType = 'success' | 'warning' | 'error' | 'info';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: number) => void;
}

const colors: Record<ToastType, { bg: string; border: string; color: string }> = {
  success: { bg: 'var(--accent-green-muted)', border: 'rgba(63,185,80,0.4)', color: 'var(--accent-green)' },
  warning: { bg: 'var(--accent-yellow-muted)', border: 'rgba(210,153,34,0.4)', color: 'var(--accent-yellow)' },
  error:   { bg: 'var(--accent-red-muted)',    border: 'rgba(248,81,73,0.4)',  color: 'var(--accent-red)' },
  info:    { bg: 'var(--accent-blue-muted)',   border: 'rgba(56,139,253,0.4)', color: 'var(--accent-blue)' },
};

const icons: Record<ToastType, string> = {
  success: '✓',
  warning: '⚠',
  error: '✕',
  info: 'ℹ',
};

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        maxWidth: '360px',
        width: 'calc(100vw - 48px)',
      }}
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const style = colors[toast.type];
        return (
          <div
            key={toast.id}
            className="toast-enter"
            style={{
              background: style.bg,
              border: `1px solid ${style.border}`,
              borderRadius: 'var(--radius-lg)',
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
            }}
          >
            <span style={{ color: style.color, fontWeight: 600, fontSize: '0.9rem', flexShrink: 0 }}>
              {icons[toast.type]}
            </span>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-primary)', flex: 1, lineHeight: 1.4 }}>
              {toast.message}
            </span>
            <button
              onClick={() => onDismiss(toast.id)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-muted)', fontSize: '0.9rem',
                flexShrink: 0, padding: '0',
              }}
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}

// Hook for managing toasts
let _nextId = 0;

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (type: ToastType, message: string, durationMs = 5000) => {
    const id = ++_nextId;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, durationMs);
  };

  const dismiss = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return {
    toasts,
    toast: {
      success: (msg: string) => addToast('success', msg),
      warning: (msg: string) => addToast('warning', msg),
      error: (msg: string) => addToast('error', msg),
      info: (msg: string) => addToast('info', msg),
    },
    dismiss,
  };
}
