import { useState } from 'react';

export default function BatchPanel({
  queryIds,
  batchPhase,
  batchProgress,
  batchAnalyzeResults,
  batchSuggestionSelections,
  batchOptimizeResults,
  batchViewQueryId,
  onBatchViewChange,
  onAnalyzeAll,
  onOptimizeAll,
  onDownload,
  onReset,
  canRun,
  selectedQueryId,
  onSelectQuery,
  batchRunIds,
}) {
  const [selected, setSelected] = useState(new Set());
  const allSelected = queryIds.length > 0 && selected.size === queryIds.length;

  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(queryIds));
  const toggleOne = (id) => setSelected((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const analyzedIds = Object.keys(batchAnalyzeResults);
  const successfulAnalyzeIds = analyzedIds.filter((id) => !batchAnalyzeResults[id]?.error);
  const optimizedIds = Object.keys(batchOptimizeResults);
  const successfulOptimizeIds = optimizedIds.filter((id) => !batchOptimizeResults[id]?.error);

  const canOptimizeAll = successfulAnalyzeIds.length > 0 && successfulAnalyzeIds.every((id) => (batchSuggestionSelections[id]?.size ?? 0) > 0);
  const isActive = batchPhase !== 'idle';
  const isClickable = batchPhase === 'review' || batchPhase === 'results';

  const getQueryStatus = (id) => {
    if (batchPhase === 'analyzing' || batchPhase === 'review') {
      const r = batchAnalyzeResults[id];
      if (!r) return { type: 'running', color: 'var(--accent)' };
      if (r.error) return { type: 'error', color: '#f85149', label: '✗' };
      return { type: 'ok', color: '#3fb950', label: '✓' };
    }
    // optimizing or results
    const ar = batchAnalyzeResults[id];
    if (ar?.error) return { type: 'skipped', color: 'var(--text-dim)', label: '—' };
    const or = batchOptimizeResults[id];
    if (!or) return { type: 'running', color: 'var(--success)' };
    if (or.error) return { type: 'error', color: '#f85149', label: '✗' };
    return { type: 'ok', color: '#3fb950', label: '✓' };
  };

  const activeList = isActive ? (batchRunIds ?? []) : [];

  return (
    <div className="card">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div className="card-title" style={{ margin: 0 }}>
          Batch Processing
          {batchPhase === 'analyzing' && <span className="badge" style={{ marginLeft: 8, background: 'rgba(88,166,255,0.15)', color: 'var(--accent)' }}>AGENT 1</span>}
          {batchPhase === 'review' && <span className="badge" style={{ marginLeft: 8, background: 'rgba(210,153,34,0.15)', color: 'var(--warning)' }}>REVIEW</span>}
          {batchPhase === 'optimizing' && <span className="badge" style={{ marginLeft: 8, background: 'rgba(63,185,80,0.15)', color: 'var(--success)' }}>AGENT 2</span>}
          {batchPhase === 'results' && <span className="badge" style={{ marginLeft: 8, background: 'rgba(63,185,80,0.15)', color: 'var(--success)' }}>DONE</span>}
        </div>
        {isActive && (
          <button onClick={onReset} style={ghostBtnStyle} title="Start over">&#x21bb; Reset</button>
        )}
      </div>

      {/* IDLE: checkbox selection */}
      {batchPhase === 'idle' && (
        <>
          {queryIds.length === 0 ? (
            <div style={{ fontSize: 13, color: 'var(--text-dim)', padding: '8px 0' }}>
              Upload an Excel file above to enable batch processing.
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                <button onClick={toggleAll} style={ghostBtnStyle}>
                  {allSelected ? 'Clear All' : 'Select All'}
                </button>
                <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                  {selected.size} / {queryIds.length} selected
                </span>
              </div>
              <div style={checkboxGridStyle}>
                {queryIds.map((id) => {
                  const isPreviewing = selectedQueryId === id;
                  return (
                    <div key={id} style={checkboxLabelStyle(isPreviewing)} title="Click to preview · check to include in batch">
                      <input
                        type="checkbox"
                        checked={selected.has(id)}
                        onChange={() => toggleOne(id)}
                        style={{ accentColor: 'var(--accent)', cursor: 'pointer', flexShrink: 0 }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span
                        onClick={() => onSelectQuery?.(id)}
                        style={{
                          fontFamily: 'var(--mono)', fontSize: 11, cursor: 'pointer',
                          color: isPreviewing ? 'var(--accent)' : 'var(--text)',
                          fontWeight: isPreviewing ? 600 : 400,
                          flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}
                      >
                        {id}
                      </span>
                    </div>
                  );
                })}
              </div>
              <button
                className="btn-optimize"
                onClick={() => onAnalyzeAll([...selected])}
                disabled={!canRun || selected.size === 0}
                style={{ marginTop: 14 }}
                title={!canRun ? 'Enter API Key first' : selected.size === 0 ? 'Select at least one query' : `Analyze ${selected.size} queries with Agent 1`}
              >
                &#x1F50D; Analyze {selected.size > 0 ? `${selected.size} ` : ''}Quer{selected.size === 1 ? 'y' : 'ies'}
              </button>
            </>
          )}
        </>
      )}

      {/* ACTIVE PHASES: per-query status list */}
      {isActive && activeList.length > 0 && (
        <div style={{ maxHeight: 220, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3, marginBottom: 14 }}>
          {activeList.map((id) => {
            const status = getQueryStatus(id);
            const isViewing = batchViewQueryId === id;
            return (
              <div
                key={id}
                onClick={isClickable ? () => onBatchViewChange(id) : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '5px 10px',
                  borderRadius: 'var(--radius)',
                  border: `1px solid ${isViewing ? 'var(--accent-dim)' : 'var(--border-2)'}`,
                  background: isViewing ? 'rgba(88,166,255,0.06)' : 'transparent',
                  cursor: isClickable ? 'pointer' : 'default',
                  transition: 'border-color 0.15s, background 0.15s',
                }}
              >
                {/* Status indicator */}
                <span style={{ width: 14, height: 14, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {status.type === 'running' ? (
                    <span className="spinner" style={{
                      width: 10, height: 10, borderWidth: 2,
                      borderColor: `${status.color}33`,
                      borderTopColor: status.color,
                    }} />
                  ) : (
                    <span style={{ fontSize: 11, color: status.color, fontWeight: 700, lineHeight: 1 }}>{status.label}</span>
                  )}
                </span>
                {/* Query ID */}
                <span style={{
                  fontFamily: 'var(--mono)', fontSize: 11, flex: 1,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  color: isViewing ? 'var(--accent)' : status.type === 'error' || status.type === 'skipped' ? 'var(--text-dim)' : 'var(--text)',
                  fontWeight: isViewing ? 600 : 400,
                }}>
                  {id}
                </span>
                {/* Error tooltip */}
                {status.type === 'error' && (
                  <span style={{ fontSize: 10, color: '#f85149', fontFamily: 'var(--mono)', maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    title={(batchAnalyzeResults[id] ?? batchOptimizeResults[id])?.error}>
                    err
                  </span>
                )}
                {/* Click hint during review/results */}
                {isClickable && !isViewing && status.type === 'ok' && (
                  <span style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--sans)' }}>view →</span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* REVIEW: stat chips + Optimize button */}
      {batchPhase === 'review' && (
        <div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={statChipStyle('#58a6ff')}>
              <span style={{ fontWeight: 700 }}>{successfulAnalyzeIds.length}</span>
              <span style={{ opacity: 0.7 }}>analyzed</span>
            </div>
            {analyzedIds.length - successfulAnalyzeIds.length > 0 && (
              <div style={statChipStyle('#f85149')}>
                <span style={{ fontWeight: 700 }}>{analyzedIds.length - successfulAnalyzeIds.length}</span>
                <span style={{ opacity: 0.7 }}>failed</span>
              </div>
            )}
            <div style={statChipStyle('#3fb950')}>
              <span style={{ fontWeight: 700 }}>
                {successfulAnalyzeIds.reduce((n, id) => n + (batchSuggestionSelections[id]?.size ?? 0), 0)}
              </span>
              <span style={{ opacity: 0.7 }}>suggestions selected</span>
            </div>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 12, lineHeight: 1.6 }}>
            Click any query above to preview and adjust suggestions. Then run Agent 2.
          </div>
          <button
            className="btn-optimize"
            onClick={onOptimizeAll}
            disabled={!canOptimizeAll}
            style={{ width: '100%', justifyContent: 'center' }}
            title={!canOptimizeAll ? 'Each analyzed query needs at least one suggestion selected' : `Optimize ${successfulAnalyzeIds.length} queries with Agent 2`}
          >
            &#x25B6; Run Agent 2 on {successfulAnalyzeIds.length} Quer{successfulAnalyzeIds.length === 1 ? 'y' : 'ies'}
          </button>
        </div>
      )}

      {/* RESULTS: stat chips + Download */}
      {batchPhase === 'results' && (
        <div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={statChipStyle('#3fb950')}>
              <span style={{ fontWeight: 700 }}>{successfulOptimizeIds.length}</span>
              <span style={{ opacity: 0.7 }}>optimized</span>
            </div>
            {optimizedIds.length - successfulOptimizeIds.length > 0 && (
              <div style={statChipStyle('#f85149')}>
                <span style={{ fontWeight: 700 }}>{optimizedIds.length - successfulOptimizeIds.length}</span>
                <span style={{ opacity: 0.7 }}>failed</span>
              </div>
            )}
          </div>
          <button
            className="btn-optimize"
            onClick={onDownload}
            disabled={successfulOptimizeIds.length === 0}
            style={{ width: '100%', justifyContent: 'center', background: 'rgba(63,185,80,0.12)', color: 'var(--success)', borderColor: 'rgba(63,185,80,0.3)' }}
          >
            &#x2B07; Download Excel
          </button>
        </div>
      )}

      {/* ANALYZING / OPTIMIZING: overall progress bar */}
      {(batchPhase === 'analyzing' || batchPhase === 'optimizing') && batchProgress && (
        <div style={{ marginTop: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="spinner" style={{
                width: 10, height: 10, borderWidth: 2,
                borderColor: 'rgba(88,166,255,0.2)',
                borderTopColor: batchPhase === 'optimizing' ? 'var(--success)' : 'var(--accent)',
                flexShrink: 0,
              }} />
              {batchPhase === 'analyzing' ? 'Agent 1' : 'Agent 2'} running in parallel
            </span>
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 600 }}>
              {batchProgress.completed} / {batchProgress.total}
            </span>
          </div>
          <div className="comparison-bar">
            <div className="comparison-bar-fill" style={{
              width: `${(batchProgress.completed / batchProgress.total) * 100}%`,
              background: batchPhase === 'optimizing' ? 'var(--success)' : undefined,
            }} />
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6 }}>
            {batchProgress.total - batchProgress.completed} remaining
          </div>
        </div>
      )}
    </div>
  );
}

const ghostBtnStyle = {
  background: 'transparent',
  border: '1px solid var(--border-2)',
  borderRadius: 'var(--radius)',
  color: 'var(--text-muted)',
  fontSize: 12,
  padding: '4px 10px',
  cursor: 'pointer',
  fontFamily: 'var(--sans)',
};

const checkboxGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
  gap: 8,
  maxHeight: 200,
  overflowY: 'auto',
  paddingRight: 4,
};

const statChipStyle = (color) => ({
  display: 'flex',
  alignItems: 'center',
  gap: 5,
  padding: '4px 10px',
  borderRadius: 20,
  border: `1px solid ${color}33`,
  background: `${color}11`,
  color,
  fontSize: 12,
  fontFamily: 'var(--sans)',
});

const checkboxLabelStyle = (checked) => ({
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 10px',
  borderRadius: 'var(--radius)',
  border: `1px solid ${checked ? 'var(--accent-dim)' : 'var(--border-2)'}`,
  background: checked ? 'rgba(88,166,255,0.06)' : 'var(--surface-2)',
  cursor: 'pointer',
  fontSize: 12,
  transition: 'border-color 0.15s, background 0.15s',
});
