// frontend/src/components/OptimizedQueryPanel.jsx
import SqlDisplay from './SqlDisplay.jsx';

export default function OptimizedQueryPanel({
  optimizerResult,
  loading,
  onRegenerate,
  onCorrectOutput,
  onRunComparison,
  sfConnected,
  comparisonLoading,
}) {
  return (
    <div className="card">
      <div
        className="card-title"
        style={{
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          Agent 2 - Optimized Query
          <span
            className="badge"
            style={{
              marginLeft: 8,
              background: 'rgba(63,185,80,0.15)',
              color: 'var(--success)',
            }}
          >
            OPTIMIZER
          </span>
        </span>
        <span style={{ display: 'flex', gap: 8 }}>
          {sfConnected && optimizerResult && (
            <button
              className="btn btn-secondary"
              style={{ fontSize: 13, padding: '2px 10px' }}
              onClick={onRunComparison}
              disabled={comparisonLoading}
              title="Execute on Snowflake and compare KPIs"
            >
              &#9654; Run on Snowflake
            </button>
          )}
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
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 14,
            padding: '32px 0',
          }}
        >
          <span
            className="spinner"
            style={{
              width: 28,
              height: 28,
              borderWidth: 3,
              borderColor: 'rgba(63,185,80,0.2)',
              borderTopColor: 'var(--success)',
            }}
          />
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                fontSize: 13,
                color: 'var(--text)',
                fontWeight: 600,
                fontFamily: 'var(--sans)',
                marginBottom: 4,
              }}
            >
              Agent 2 rewriting query...
            </div>
            <div
              style={{
                fontSize: 11,
                color: 'var(--text-dim)',
                fontFamily: 'var(--sans)',
              }}
            >
              Applying selected optimizations
            </div>
          </div>
        </div>
      )}

      {!loading && !optimizerResult && (
        <div className="empty-state">
          <div className="icon">&#x2728;</div>
          The optimized SQL will appear here after running.
        </div>
      )}

      {!loading && optimizerResult && (optimizerResult.schema_violations ?? []).length > 0 && (
        <div
          style={{
            background: 'rgba(210,153,34,0.12)',
            border: '1px solid rgba(210,153,34,0.4)',
            borderRadius: 6,
            padding: '8px 12px',
            marginBottom: 10,
            fontSize: 12,
            fontFamily: 'var(--sans)',
            color: 'var(--warning, #d2991a)',
          }}
        >
          <strong>Schema warning:</strong> optimized query references column(s) not found in fetched
          schema — may be CTE aliases or hallucinated names. Verify before running:{' '}
          <code style={{ fontSize: 11 }}>
            {(optimizerResult.schema_violations ?? []).join(', ')}
          </code>
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
          {optimizerResult.change_summary && (
            <div style={{ marginTop: 14 }}>
              <div
                className="explanation-label"
                style={{ color: 'var(--success)' }}
              >
                Change Summary
              </div>
              <div
                className="explanation-block"
                style={{ whiteSpace: 'pre-wrap' }}
              >
                {optimizerResult.change_summary}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
