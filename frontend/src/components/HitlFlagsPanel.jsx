// frontend/src/components/HitlFlagsPanel.jsx
import { useState } from 'react';

export default function HitlFlagsPanel({ flags, onConfirm, onSkip }) {
  const [values, setValues] = useState({});

  const handleChange = (id, value) => {
    setValues((prev) => ({ ...prev, [id]: value }));
  };

  const handleConfirm = () => {
    const resolved = flags
      .filter((f) => values[f.id]?.trim())
      .map((f) => ({ id: f.id, value: values[f.id].trim() }));
    onConfirm(resolved);
  };

  return (
    <div
      className="card"
      style={{ marginBottom: 16, borderColor: 'rgba(255,193,7,0.35)' }}
    >
      <div
        className="card-title"
        style={{ marginBottom: 14 }}
      >
        Human Input Required
        <span
          className="badge"
          style={{
            marginLeft: 8,
            background: 'rgba(255,193,7,0.12)',
            color: '#e3b341',
          }}
        >
          STEP 1.5
        </span>
      </div>

      {flags.map((flag) => (
        <div key={flag.id} style={{ marginBottom: 18 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: 'var(--text)',
              fontFamily: 'var(--sans)',
              marginBottom: 4,
            }}
          >
            {flag.title}
          </div>
          <div
            style={{
              fontSize: 12,
              color: 'var(--text-dim)',
              fontFamily: 'var(--sans)',
              marginBottom: 8,
            }}
          >
            {flag.description}
          </div>
          {flag.sql_snippet && (
            <div
              style={{
                fontSize: 11,
                fontFamily: 'var(--font)',
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                borderRadius: 4,
                padding: '4px 8px',
                marginBottom: 8,
                color: 'var(--accent)',
              }}
            >
              {flag.sql_snippet}
            </div>
          )}
          <input
            type="text"
            className="field input"
            placeholder={flag.placeholder}
            value={values[flag.id] || ''}
            onChange={(e) => handleChange(flag.id, e.target.value)}
            style={{ width: '100%', boxSizing: 'border-box' }}
          />
        </div>
      ))}

      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 8,
          marginTop: 8,
        }}
      >
        <button
          onClick={onSkip}
          style={{
            background: 'none',
            border: '1px solid var(--border-2)',
            borderRadius: 'var(--radius)',
            cursor: 'pointer',
            fontSize: 12,
            color: 'var(--text-dim)',
            fontFamily: 'var(--sans)',
            padding: '5px 14px',
          }}
        >
          Skip flags
        </button>
        <button
          className="btn-optimize"
          onClick={handleConfirm}
          style={{ fontSize: 12, padding: '5px 14px', minWidth: 'unset' }}
        >
          Apply &amp; Optimize
        </button>
      </div>
    </div>
  );
}
