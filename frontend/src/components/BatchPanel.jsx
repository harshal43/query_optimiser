import { useState } from 'react';

/** * BatchPanel - multi-phase batch workflow control panel.
 * * Phases: idle -> analyzing -> review -> optimizing -> results
 *
 * Props:
 *   queryIds                     : string[]
 *   batchPhase                   : 'idle'|'analyzing'|'review'|'optimizing'|'results'
 *   batchProgress                : { current, total, currentId, agentLabel } | null
 *   batchAnalyzeResults          : Record<queryId, analyzeResult | { error: string }>
 *   batchSuggestionSelections    : Record<queryId, Set<number>>
 *   batchOptimizeResults         : Record<queryId, optimizeResult | { error: string }>
 *   batchViewQueryId             : string
 *   onBatchViewChange            : (queryId: string) => void
 *   onAnalyzeAll                 : (selectedIds: string[]) => void
 *   onOptimizeAll                : () => void
 *   onDownload                   : () => void
 *   onReset                      : () => void
 *   canRun                       : bool
 */
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

  return (
    <div className="card">
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
                  const isActive = selectedQueryId === id;
                  return (
                    <div
                      key={id}
                      style={checkboxLabelStyle(isActive)}
                      title="Click to preview query · check to include in batch"
                    >
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
                          color: isActive ? 'var(--accent)' : 'var(--text)',
                          fontWeight: isActive ? 600 : 400,
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
                title={!canRun ? 'Enter API Key and Endpoint URL first' : selected.size === 0 ? 'Select at least one query' : `Analyze ${selected.size} quer${selected.size === 1 ? 'y' : 'ies'} with Agent 1`}
                style={{ marginTop: 14 }}
              >
                &#x1F50D; Analyze {selected.size > 0 ? `${selected.size} ` : ''}Quer{selected.size === 1 ? 'y' : 'ies'}
              </button>
            </>
          )}
        </>
      )}

      {(batchPhase === 'analyzing' || batchPhase === 'optimizing') && batchProgress && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="spinner" style={{ width: 10, height: 10, borderWidth: 2, borderColor: 'rgba(88,166,255,0.2)', borderTopColor: batchPhase === 'optimizing' ? 'var(--success)' : 'var(--accent)', flexShrink: 0 }} />
              {batchPhase === 'analyzing' ? 'Agent 1 analyzing' : 'Agent 2 optimizing'} in parallel
            </span>
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 600 }}>
              {batchProgress.completed} / {batchProgress.total}
            </span>
          </div>
          <div className="comparison-bar">
            <div className="comparison-bar-fill" style={{ width: `${(batchProgress.completed / batchProgress.total) * 100}%`, background: batchPhase === 'optimizing' ? 'var(--success)' : undefined }} />
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8 }}>
            {batchProgress.total - batchProgress.completed} remaining · running up to 5 at once
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