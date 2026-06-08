import { useState, useEffect } from 'react';
import { fetchSnowflakeQueries } from '../services/api.js';

const TABS = [
  { key: 'credits',   label: '💰 Top Spenders',      desc: 'Ranked by total credits consumed (last 30 days)' },
  { key: 'frequency', label: '🔁 Repeat Offenders',  desc: 'Ranked by execution count (last 30 days)' },
  { key: 'killer',    label: '☠️ Killers',           desc: 'Ranked by credits \xD7 frequency composite score' },
  { key: 'all',       label: '📋 All History',       desc: 'Raw query history — last 30 days, most recent first' },
];

const TH = { padding: '6px 10px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap', textAlign: 'right' };
const TD = { padding: '8px 10px', color: 'var(--text)', verticalAlign: 'middle' };

export default function SnowflakeDashboard({ account, onSelectQuery, onDisconnect, onCheckConnection }) {
  const [category, setCategory] = useState('credits');
  const [rows, setRows]         = useState([]);
  const [loading, setLoading]   = useState(false);
  const [fetchErr, setFetchErr] = useState('');
  const [checking, setChecking] = useState(false);
  const [checkMsg, setCheckMsg] = useState('');

  useEffect(() => {
    setRows([]);
    setFetchErr('');
    setLoading(true);
    fetchSnowflakeQueries(category)
      .then(data => setRows(data.rows))
      .catch(err  => setFetchErr(err.message))
      .finally(() => setLoading(false));
  }, [category]);

  const handleCheck = async () => {
    setChecking(true); setCheckMsg('');
    try {
      const status = await onCheckConnection();
      setCheckMsg(status?.connected ? `✓ Connected to ${status.account}` : '⚠ Connection lost');
    } catch (err) {
      setCheckMsg(`⚠ ${err.message}`);
    } finally {
      setChecking(false);
      setTimeout(() => setCheckMsg(''), 4000);
    }
  };

  const hasFrequency = rows.length > 0 && rows[0].frequency !== null;
  const hasScore     = rows.length > 0 && rows[0].score !== null;
  const activeTab    = TABS.find(t => t.key === category);

  return (
    <div className="card">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--sans)' }}>
            &#x2744;&#xFE0F; Snowflake Dashboard
          </span>
          <span style={{
            fontSize: 11, color: 'var(--success)', fontFamily: 'var(--mono)',
            background: 'rgba(74,222,128,0.12)', padding: '2px 9px', borderRadius: 4,
          }}>
            &#x25CF; {account}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {checkMsg && (
            <span style={{ fontSize: 11, color: checkMsg.startsWith('✓') ? 'var(--success)' : '#f87171', fontFamily: 'var(--mono)' }}>
              {checkMsg}
            </span>
          )}
          <button
            onClick={handleCheck} disabled={checking}
            style={{
              padding: '5px 12px', fontSize: 11, borderRadius: 'var(--radius)',
              border: '1px solid var(--border-2)', background: 'var(--surface-2)',
              color: 'var(--text)', cursor: checking ? 'not-allowed' : 'pointer',
              fontFamily: 'var(--sans)', display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            {checking
              ? <><span className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5 }} /> Checking...</>
              : '🔌 Check Connection'}
          </button>
          <button
            onClick={onDisconnect}
            style={{
              padding: '5px 12px', fontSize: 11, borderRadius: 'var(--radius)',
              border: '1px solid var(--border-2)', background: 'var(--surface-2)',
              color: '#f87171', cursor: 'pointer', fontFamily: 'var(--sans)',
            }}
          >
            Disconnect
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12, borderBottom: '1px solid var(--border)', paddingBottom: 10, flexWrap: 'wrap' }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setCategory(tab.key)}
            style={{
              padding: '6px 14px', fontSize: 12, borderRadius: 'var(--radius)',
              border: '1px solid var(--border-2)',
              background: category === tab.key ? 'var(--accent)' : 'var(--surface-2)',
              color: category === tab.key ? '#fff' : 'var(--text)',
              cursor: 'pointer', fontFamily: 'var(--sans)', whiteSpace: 'nowrap',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 12, fontFamily: 'var(--sans)' }}>
        {activeTab?.desc} &mdash; click any row to load it for optimization
      </div>

      {/* Body */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <span className="spinner" /> Fetching from Snowflake...
        </div>
      )}

      {fetchErr && !loading && (
        <div className="error-box">&#x26A0; {fetchErr}</div>
      )}

      {!loading && !fetchErr && rows.length === 0 && (
        <div style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)', fontSize: 13 }}>
          No queries found for the last 30 days.
        </div>
      )}

      {!loading && rows.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: 'var(--mono)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ ...TH, textAlign: 'right', width: 36 }}>#</th>
                <th style={{ ...TH, textAlign: 'left' }}>Query</th>
                <th style={TH}>Credits</th>
                {hasFrequency && <th style={TH}>Executions</th>}
                {hasScore     && <th style={TH}>Score</th>}
                <th style={TH}>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={`${row.query_id}-${i}`}
                  style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.1s' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  onClick={() => onSelectQuery(row)}
                >
                  <td style={{ ...TD, textAlign: 'right', color: 'var(--text-dim)' }}>{i + 1}</td>
                  <td style={{ ...TD, maxWidth: 520, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    title={row.query_text}>
                    {row.query_text}
                  </td>
                  <td style={{ ...TD, textAlign: 'right' }}>
                    {(row.credits || 0).toFixed(4)}
                  </td>
                  {hasFrequency && (
                    <td style={{ ...TD, textAlign: 'right' }}>
                      {row.frequency?.toLocaleString() ?? '—'}
                    </td>
                  )}
                  {hasScore && (
                    <td style={{ ...TD, textAlign: 'right' }}>
                      {row.score != null ? (row.score).toFixed(2) : '—'}
                    </td>
                  )}
                  <td style={{ ...TD, textAlign: 'center' }}>
                    <button
                      onClick={e => { e.stopPropagation(); onSelectQuery(row); }}
                      style={{
                        padding: '3px 10px', fontSize: 11, borderRadius: 4,
                        border: '1px solid var(--accent-dim)', background: 'transparent',
                        color: 'var(--accent)', cursor: 'pointer', whiteSpace: 'nowrap',
                      }}
                    >
                      Optimize &#x2192;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', textAlign: 'right', marginTop: 8, fontFamily: 'var(--mono)' }}>
            {rows.length} rows
          </div>
        </div>
      )}
    </div>
  );
}
