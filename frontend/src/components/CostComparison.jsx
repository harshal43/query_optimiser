/** * Credit Comparison - Original query vs Estimated optimized query.
 *
 * Props:
 *   costComparison: {
 *     original_credits,
 *     estimated_optimized_credits,
 *     credits_saved,
 *     savings_percentage,
 *     savings_reasoning,
 *   } | null
 */
export default function CostComparison({ costComparison }) {
  if (!costComparison) return null;

  const { original_credits, estimated_optimized_credits, credits_saved, savings_percentage, savings_reasoning, } = costComparison;

  const fmtCredits = (v) => typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 6 }) : v;

  return (
    <div className="card">
      <div className="card-title">
        Snowflake Credits - Original vs Estimated Optimized
        {savings_percentage > 0 && (
          <span className="badge" style={{ background: 'rgba(63,185,80,0.15)', color: 'var(--success)', marginLeft: 8 }}>
            &#x2193; {savings_percentage}% credits saved
          </span>
        )}
      </div>

      <div className="comparison-cards">
        <div className="comparison-card">
          <span className="label">&#x2744; Original Credits</span>
          <span className="value yellow">{fmtCredits(original_credits)}</span>
          <span className="sub">Actual credits consumed</span>
        </div>
        <div className="comparison-card">
          <span className="label">&#x2728; Estimated Optimized Credits</span>
          <span className="value green">{fmtCredits(estimated_optimized_credits)}</span>
          <span className="sub">LLM-estimated after optimization</span>
        </div>
        <div className="comparison-card">
          <span className="label">&#x0394; Credits Saved</span>
          <span className="value green">{fmtCredits(credits_saved)}</span>
          <span className="sub">Original - Optimized</span>
        </div>
        <div className="comparison-card">
          <span className="label">% Improvement</span>
          <span className="value green">{savings_percentage.toFixed(2)}%</span>
          <span className="sub">Estimated credit reduction</span>
        </div>
      </div>

      {savings_reasoning && (
        <div style={{ marginTop: 14, padding: '10px 14px', background: 'var(--bg)', border: '1px solid var(--border)', borderLeft: '3px solid var(--success)', borderRadius: 'var(--radius)', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--success)', display: 'block', marginBottom: 4 }}>LLM Reasoning</span>
          {savings_reasoning}
        </div>
      )}
    </div>
  );
}