import { useState } from 'react';

export default function SuggestionsPanel({ analyzeResult, analyzing, selectedNums, onToggle, onOptimize, optimizing, canOptimize, hideOptimizeButton, }) {
  const [collapsed, setCollapsed] = useState(false);

  const suggestions = analyzeResult?.parsed_suggestions ?? [];
  const allChecked = suggestions.length > 0 && suggestions.every((s) => selectedNums.has(s.number));
  const noneChecked = suggestions.every((s) => !selectedNums.has(s.number));

  const handleSelectAll = () => {
    suggestions.forEach((s) => { if (!selectedNums.has(s.number)) onToggle(s.number); });
  };
  const handleDeselectAll = () => {
    suggestions.forEach((s) => { if (selectedNums.has(s.number)) onToggle(s.number); });
  };

  const hasContent = !analyzing && suggestions.length > 0;

  return (
    <div className="card">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: collapsed && hasContent ? 0 : 14 }}>
        <div
          className="card-title"
          style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8, cursor: hasContent ? 'pointer' : 'default', userSelect: 'none' }}
          onClick={() => hasContent && setCollapsed((v) => !v)}
          title={hasContent ? (collapsed ? 'Expand suggestions' : 'Collapse suggestions') : undefined}
        >
          Agent 1 - Optimization Advisor
          <span className="badge">ADVISOR</span>
          {hasContent && (
            <span style={{ fontSize: 13, color: 'var(--text-dim)', marginLeft: 2, transition: 'transform 0.2s', display: 'inline-block', transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
              &#x25BE;
            </span>
          )}
          {collapsed && hasContent && (
            <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--sans)', fontWeight: 400, marginLeft: 4 }}>
              {selectedNums.size} / {suggestions.length} selected
            </span>
          )}
        </div>
        {!collapsed && suggestions.length > 0 && (
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={handleSelectAll} disabled={allChecked} style={smallBtnStyle}>All</button>
            <button onClick={handleDeselectAll} disabled={noneChecked} style={smallBtnStyle}>None</button>
          </div>
        )}
      </div>

      {/* Loading */}
      {analyzing && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '32px 0' }}>
          <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3, borderColor: 'rgba(88,166,255,0.2)', borderTopColor: 'var(--accent)' }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600, fontFamily: 'var(--sans)', marginBottom: 4 }}>
              Agent 1 analyzing query...
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--sans)' }}>
              Identifying optimization opportunities
            </div>
          </div>
        </div>
      )}

      {/* Empty */}
      {!analyzing && !analyzeResult && (
        <div className="empty-state">
          <div className="icon">&#x1F4A1;</div>
          Click <strong>Analyze</strong> to get optimization suggestions.
        </div>
      )}

      {/* Suggestions list — hidden when collapsed */}
      {!collapsed && !analyzing && suggestions.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
          {suggestions.map((s) => {
            const checked = selectedNums.has(s.number);
            return (
              <label
                key={s.number}
                style={{
                  display: 'flex', gap: 12, padding: '10px 12px',
                  borderRadius: 'var(--radius)',
                  border: `1px solid ${checked ? 'var(--accent-dim)' : 'var(--border)'}`,
                  background: checked ? 'rgba(31,111,235,0.06)' : 'var(--bg)',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s, background 0.15s',
                  alignItems: 'flex-start',
                }}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(s.number)}
                  style={{ marginTop: 3, accentColor: 'var(--accent)', cursor: 'pointer', flexShrink: 0 }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: checked ? 'var(--text)' : 'var(--text-muted)', marginBottom: s.body ? 5 : 0 }}>
                    {s.number}. {s.title}
                  </div>
                  {s.body && (
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                      {s.body}
                    </div>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      )}

      {/* Apply button */}
      {!collapsed && !analyzing && suggestions.length > 0 && !hideOptimizeButton && (
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'center' }}>
          <button
            className="btn-optimize"
            onClick={onOptimize}
            disabled={!canOptimize}
            style={{ width: '100%', justifyContent: 'center' }}
            title={selectedNums.size === 0 ? 'Select at least one suggestion' : 'Run Agent 2 with selected suggestions'}
          >
            {optimizing ? (<> <span className="spinner" /> Optimizing...</>) : (<> &#x25B6; Apply {selectedNums.size} Selected Suggestion{selectedNums.size !== 1 ? 's' : ''}</>)}
          </button>
        </div>
      )}
    </div>
  );
}

const smallBtnStyle = {
  background: 'var(--surface-2)',
  border: '1px solid var(--border-2)',
  borderRadius: 5,
  color: 'var(--text-muted)',
  fontSize: 11,
  padding: '3px 10px',
  cursor: 'pointer',
  fontFamily: 'var(--sans)',
};
