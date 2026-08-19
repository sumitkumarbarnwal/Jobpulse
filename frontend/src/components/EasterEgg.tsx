import { useEffect, useRef, useState } from 'react';

const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];

export function EasterEgg() {
  const [active, setActive] = useState(false);
  const sequenceRef = useRef<string[]>([]);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      sequenceRef.current.push(e.key);

      // Keep only the last N keys
      if (sequenceRef.current.length > KONAMI.length) {
        sequenceRef.current = sequenceRef.current.slice(-KONAMI.length);
      }

      if (sequenceRef.current.join(',') === KONAMI.join(',')) {
        setActive(true);
        sequenceRef.current = [];

        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => setActive(false), 5000);
      }
    };

    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('keydown', handleKey);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  if (!active) return null;

  return (
    <div
      id="easter-egg"
      className="easter-egg"
      style={{
        position: 'fixed',
        bottom: '80px',
        left: '50%',
        zIndex: 200,
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-xl)',
        padding: '16px 24px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        textAlign: 'center',
        maxWidth: '320px',
      }}
    >
      <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🛠️</div>
      <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '4px' }}>
        Nice. You found the engineering backdoor.
      </div>
      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
        ↑↑↓↓←→←→BA — classic.
      </div>
    </div>
  );
}
