import { useState } from 'react';

const FIELDS = [
  { key: 'account',     label: 'Account',    placeholder: 'myorg-myaccount',  required: true  },
  { key: 'user',        label: 'Username',   placeholder: 'MYUSER',           required: true  },
  { key: 'password',    label: 'Password',   placeholder: '••••••••',         required: true, type: 'password' },
  { key: 'role',        label: 'Role',       placeholder: 'SYSADMIN (optional)'               },
  { key: 'warehouse',   label: 'Warehouse',  placeholder: 'COMPUTE_WH (optional)'             },
  { key: 'database',    label: 'Database',   placeholder: 'MY_DATABASE (optional)'            },
  { key: 'schema_name', label: 'Schema',     placeholder: 'PUBLIC (optional)'                 },
];

const EMPTY = { account: '', user: '', password: '', role: '', warehouse: '', database: '', schema_name: '' };

export default function SnowflakeConnectModal({ onConnect, onClose, connecting, error }) {
  const [form, setForm] = useState(EMPTY);

  const set = (key, val) => setForm(prev => ({ ...prev, [key]: val }));
  const handleSubmit = (e) => { e.preventDefault(); onConnect(form); };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.72)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border-2)', borderRadius: 10,
        padding: '28px 32px', width: 420, maxWidth: '90vw', boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
      }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--sans)', marginBottom: 20 }}>
          &#x2744;&#xFE0F; Connect to Snowflake
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
          {FIELDS.map(({ key, label, placeholder, required, type }) => (
            <div key={key} className="field" style={{ marginBottom: 0 }}>
              <label>
                {label}
                {required && <span style={{ color: '#f87171' }}> *</span>}
              </label>
              <input
                type={type || 'text'}
                value={form[key]}
                onChange={e => set(key, e.target.value)}
                placeholder={placeholder}
                required={required}
                autoComplete={key === 'password' ? 'current-password' : 'off'}
              />
            </div>
          ))}

          {error && (
            <div style={{
              color: '#f87171', fontSize: 12, padding: '8px 10px',
              background: 'rgba(248,113,113,0.1)', borderRadius: 6,
            }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, marginTop: 6, justifyContent: 'flex-end' }}>
            <button
              type="button" onClick={onClose} disabled={connecting}
              style={{
                padding: '7px 18px', background: 'var(--surface-2)', border: '1px solid var(--border-2)',
                borderRadius: 'var(--radius)', color: 'var(--text)', cursor: connecting ? 'not-allowed' : 'pointer',
                fontFamily: 'var(--sans)', fontSize: 13, opacity: connecting ? 0.5 : 1,
              }}
            >
              Cancel
            </button>
            <button type="submit" disabled={connecting} className="btn-optimize" style={{ padding: '7px 20px' }}>
              {connecting
                ? <><span className="spinner" /> Connecting...</>
                : 'Connect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
