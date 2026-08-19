import { useState } from 'react';
import { triggerIngestion } from '../services/api';
import type { IngestionTriggerResponse } from '../types';

interface ScenarioTesterProps {
  onComplete: (result: IngestionTriggerResponse) => void;
  onError: (message: string) => void;
}

export function ScenarioTester({ onComplete, onError }: ScenarioTesterProps) {
  const [activeScenario, setActiveScenario] = useState<string | null>(null);

  const runScenario = async (source?: string, scenario?: string) => {
    const scenarioKey = scenario || source || 'arbeitnow';
    setActiveScenario(scenarioKey);
    try {
      const result = await triggerIngestion(source, scenario);
      onComplete(result);
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Scenario execution failed');
    } finally {
      setActiveScenario(null);
    }
  };

  return (
    <div className="surface p-4" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
            🧪 Interactive Resilience & Failure Scenario Harness
          </span>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
            Click any button below to trigger and observe live resilience mechanisms in real-time.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', paddingTop: '4px' }}>
        {/* Scenario 1: Normal */}
        <button
          className="btn btn-secondary"
          onClick={() => runScenario('arbeitnow')}
          disabled={activeScenario !== null}
          title="Fetch live Arbeitnow API data (200 OK)"
          style={{ fontSize: '0.8rem' }}
        >
          {activeScenario === 'arbeitnow' ? 'Running...' : '1. Live Sync (Arbeitnow 200)'}
        </button>

        {/* Scenario 2: Duplicate */}
        <button
          className="btn btn-secondary"
          onClick={() => runScenario('mock', 'normal')}
          disabled={activeScenario !== null}
          title="Fetch dataset again to verify composite key deduplication (0 new, N dupes)"
          style={{ fontSize: '0.8rem' }}
        >
          {activeScenario === 'normal' ? 'Running...' : '2. Test Duplicate Check'}
        </button>

        {/* Scenario 3: Rate Limited */}
        <button
          className="btn btn-secondary"
          onClick={() => runScenario('mock', 'rate_limited')}
          disabled={activeScenario !== null}
          title="Simulate HTTP 429 Too Many Requests & observe backoff/retry handling"
          style={{ fontSize: '0.8rem', borderColor: 'rgba(210,153,34,0.4)', color: 'var(--accent-yellow)' }}
        >
          {activeScenario === 'rate_limited' ? 'Running...' : '3. Test Rate Limit (429)'}
        </button>

        {/* Scenario 4: API Failure */}
        <button
          className="btn btn-secondary"
          onClick={() => runScenario('mock', 'server_error')}
          disabled={activeScenario !== null}
          title="Simulate HTTP 500 Server Error to test retries, Circuit Breaker OPEN, and Cached Data fallback"
          style={{ fontSize: '0.8rem', borderColor: 'rgba(248,81,73,0.4)', color: 'var(--accent-red)' }}
        >
          {activeScenario === 'server_error' ? 'Running...' : '4. Test API Failure (500 / Circuit Breaker)'}
        </button>

        {/* Scenario 5: Empty Response */}
        <button
          className="btn btn-secondary"
          onClick={() => runScenario('mock', 'empty')}
          disabled={activeScenario !== null}
          title="Simulate empty [] response to verify database preservation rule (0 jobs deleted)"
          style={{ fontSize: '0.8rem', borderColor: 'rgba(210,153,34,0.4)', color: 'var(--accent-orange)' }}
        >
          {activeScenario === 'empty' ? 'Running...' : '5. Test Empty Response ([])'}
        </button>
      </div>
    </div>
  );
}
