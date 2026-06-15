import { useState, useEffect } from 'react';
import { qualifyStrategy } from '../services/api.js';

const PRIORITIES = [
  { value: 'cost_savings', label: 'Cost Savings — reduce Snowflake credits' },
  { value: 'balanced',     label: 'Balanced — balance cost and speed' },
  { value: 'speed',        label: 'Speed — fastest execution, cost secondary' },
];

const TOLERANCES = [
  { value: 'minimal',  label: 'Minimal — safe micro-optimizations only' },
  { value: 'standard', label: 'Standard — standard rewrites acceptable' },
  { value: 'major',    label: 'Major — full restructure permitted' },
];

const TIER_COLORS = {
  conservative: { bg: 'rgba(88,166,255,0.08)', border: 'var(--accent-dim)', text: 'var(--accent)' },
  balanced:     { bg: 'rgba(63,185,80,0.08)',  border: 'rgba(63,185,80,0.4)', text: 'var(--success)' },
  aggressive:   { bg: 'rgba(255,123,114,0.08)', border: 'rgba(255,123,114,0.4)', text: '#f85149' },
};

const TIER_LABEL = {
  conservative: 'Conservative',
  balanced:     'Balanced',
  aggressive:   'Aggressive',
};

export default function HitlPanel({ onConfirm, onReset }) {
  const [priority, setPriority]           = useState('');
  const [tolerance, setTolerance]         = useState('');
  const [qualifying, setQualifying]       = useState(false);
  const [recommended, setRecommended]     = useState(null);
  const [rulesPreview, setRulesPreview]   = useState(null);
  const [overrideTier, setOverrideTier]   = useState('');
  const [showRules, setShowRules]         = useState(false);
  const [confirmed, setConfirmed]         = useState(false);
  const [error, setError]                 = useState('');

  const effectiveTier = overrideTier || recommended;

  useEffect(() => {
    if (!priority || !tolerance) {
      setRecommended(null);
      setRulesPreview(null);
      setOverrideTier('');
      setConfirmed(false);
      onReset();
      return;
    }
    setQualifying(true);
    setError('');
    qualifyStrategy(priority, tolerance)
      .then((res) => {
        setRecommended(res.recommended_tier);
        setRulesPreview(res.rules_preview);
        setOverrideTier('');
        setConfirmed(false);
        onReset();
      })
      .catch((err) => setError(`Strategy qualification failed: ${err.message}`))
      .finally(() => setQualifying(false));
  }, [priority, tolerance]);

  const handleConfirm = () => {
    if (!effectiveTier) return;
    setConfirmed(true);
    onConfirm(effectiveTier);
  };

  const handleChange = () => {
    setConfirmed(false);
    onReset();
  };

  const colors = effectiveTier ? TIER_COLORS[effectiveTier] : null;

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-title" style={{ marginBottom: 14 }}>
        Strategy Questionnaire
        <span className="badge" style={{ marginLeft: 8, background: 'rgba(163,113,247,0.15)', color: '#a371f7' }}>STEP 0</span>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <div className="field" style={{ flex: 1, minWidth: 220, marginBottom: 0 }}>
          <label>Business Priority</label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            disabled={confirmed}
          >
            <option value="">Select priority...</option>
            {PRIORITIES.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        <div className="field" style={{ flex: 1, minWidth: 220, marginBottom: 0 }}>
          <label>Change Tolerance</label>
          <select
            value={tolerance}
            onChange={(e) => setTolerance(e.target.value)}
            disabled={confirmed}
          >
            <option value="">Select tolerance...</option>
            {TOLERANCES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      {qualifying && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--sans)' }}>
          <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, borderColor: 'rgba(88,166,255,0.2)', borderTopColor: 'var(--accent)' }} />
          Calculating recommended strategy...
        </div>
      )}

      {error && (
        <div style={{ fontSize: 12, color: '#f85149', fontFamily: 'var(--sans)' }}>{error}</div>
      )}

      {!qualifying && effectiveTier && (
        <div style={{
          background: colors.bg,
          border: `1px solid ${colors.border}`,
          borderRadius: 'var(--radius)',
          padding: '10px 14px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: colors.text, fontFamily: 'var(--sans)' }}>
                ✦ {confirmed ? 'Strategy:' : 'Recommended:'} {TIER_LABEL[effectiveTier]}
              </span>
              {!confirmed && recommended && (
                <div className="field" style={{ marginBottom: 0 }}>
                  <select
                    value={overrideTier}
                    onChange={(e) => setOverrideTier(e.target.value)}
                    style={{ fontSize: 11, padding: '3px 8px', height: 'auto' }}
                  >
                    <option value="">Use recommended</option>
                    <option value="conservative">Conservative</option>
                    <option value="balanced">Balanced</option>
                    <option value="aggressive">Aggressive</option>
                  </select>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {rulesPreview && !confirmed && (
                <button
                  onClick={() => setShowRules((v) => !v)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--sans)', padding: '3px 6px' }}
                >
                  {showRules ? '▾ Hide rules' : '▸ Show rules'}
                </button>
              )}
              {!confirmed ? (
                <button
                  className="btn-optimize"
                  onClick={handleConfirm}
                  style={{ fontSize: 12, padding: '5px 14px', minWidth: 'unset' }}
                >
                  ✓ Confirm
                </button>
              ) : (
                <button
                  onClick={handleChange}
                  style={{ background: 'none', border: '1px solid var(--border-2)', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--sans)', padding: '4px 10px' }}
                >
                  Change
                </button>
              )}
            </div>
          </div>

          {showRules && !confirmed && rulesPreview && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
              {Object.entries(rulesPreview.advisor_rules ?? {})
                .filter(([, v]) => v)
                .map(([k]) => (
                  <span key={k} style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--sans)' }}>
                    ✓ {k.replace(/_/g, ' ')}
                  </span>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
