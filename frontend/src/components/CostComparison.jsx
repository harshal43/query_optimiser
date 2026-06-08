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
  const optimizedBarPct = original_credits > 0 ? Math.min((estimated_optimized_credits / original_credits) * 100, 100) : 0;

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

      <div className="comparison-bar-wrapper">
        <div className="comparison-bar-label">
          <span>Estimated optimized credits as % of original</span>
          <span style={{ color: 'var(--success)' }}>{optimizedBarPct.toFixed(1)}% of original</span>
        </div>
        <div className="comparison-bar" style={{ height: 12, position: 'relative' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: `${optimizedBarPct}%`, borderRadius: 6, background: 'rgba(63,185,80,0.18)', transition: 'width 0.6s ease' }} />
        </div>
        <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-dim)' }}>
          <span><span style={{ color: 'var(--warning)' }}>&#x25A0;</span> Optimized credits ({fmtCredits(estimated_optimized_credits)})</span>
          <span><span style={{ color: 'rgba(63,185,80,0.6)' }}>&#x25A0;</span> Credits saved ({fmtCredits(credits_saved)})</span>
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