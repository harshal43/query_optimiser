import SqlDisplay from './SqlDisplay.jsx';

/** * Displays Agent 2 output: optimized SQL + explanation.
 *
 * Props:
 *   optimizerResult: { optimized_query, explanation } | null
 *   loading        : bool
 */
export default function OptimizedQueryPanel({ optimizerResult, loading, onRegenerate, onCorrectOutput }) {
  return (
    <div className="card">
      <div className="card-title" style={{ marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>
          Agent 2 - Optimized Query
          <span className="badge" style={{ marginLeft: 8, background: 'rgba(63,185,80,0.15)', color: 'var(--success)' }}>OPTIMIZER</span>
        </span>
        <span style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-secondary"
            style={{ fontSize: 13, padding: '2px 10px' }}
            onClick={onRegenerate}
            disabled={loading}
            title="Regenerate optimized query"
          >
            &#x1F504; Regenerate
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: 13, padding: '2px 10px' }}
            onClick={onCorrectOutput}
            disabled={loading}
            title="Correct output (coming soon)"
          >
            &#x1F6E0; Correct Output
          </button>
        </span>
      </div>

      {loading && (
        <div className="empty-state">
          <div className="icon" style={{ fontSize: 28 }}>&#x1F504;</div>
          Rewriting query...
        </div>
      )}

      {!loading && !optimizerResult && (
        <div className="empty-state">
          <div className="icon">&#x2728;</div>
          The optimized SQL will appear here after running.
        </div>
      )}

      {!loading && optimizerResult && (
        <>
          <SqlDisplay sql={optimizerResult.optimized_query} maxHeight="260px" />
          {optimizerResult.explanation && (
            <div style={{ marginTop: 14 }}>
              <div className="explanation-label">Changes Made</div>
              <div className="explanation-block">{optimizerResult.explanation}</div>
            </div>
          )}
        </>
      )}
    </div>
  );
}