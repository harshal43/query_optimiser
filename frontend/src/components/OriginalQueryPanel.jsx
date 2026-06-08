import SqlDisplay from './SqlDisplay.jsx';

/** * Shows the selected query's SQL and Snowflake credit cost.
 *
 * Props:
 *   queryDetail : { query_id, query_text, credits } | null
 */
export default function OriginalQueryPanel({ queryDetail }) {
  if (!queryDetail) {
    return (
      <div className="card">
        <div className="card-title">Original Query</div>
        <div className="empty-state">
          <div className="icon">&#x1F4CB;</div>
          Select a Query ID above to preview the original SQL.
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <span>
          Original Query
          <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 8 }}>#{queryDetail.query_id}</span>
        </span>
        <span className="credits-badge">
          &#x2744; {queryDetail.credits.toLocaleString(undefined, { maximumFractionDigits: 4 })} Snowflake Credits
        </span>
      </div>
      <SqlDisplay sql={queryDetail.query_text} maxHeight="280px" />
    </div>
  );
}