/** * Compact token + cost summary strip.
 *
 * Props:
 *   usage: {
 *     prompt_tokens, completion_tokens, total_tokens,
 *     prompt_cost, completion_cost, total_cost
 *   }
 */
export default function TokenBadge({ usage }) {
  if (!usage) return null;

  const fmt = (n) => n.toLocaleString();
  const fmtCost = (v) => v < 0.0001 ? `$${v.toExponential(2)}` : `$${v.toFixed(6)}`;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
      <span className="token-pill">&#x2191; {fmt(usage.prompt_tokens)} prompt</span>
      <span className="token-pill">&#x2193; {fmt(usage.completion_tokens)} completion</span>
      <span className="token-pill">&#x03A3; {fmt(usage.total_tokens)} total</span>
      <span className="token-pill" style={{ background: 'rgba(63,185,80,0.08)', borderColor: 'rgba(63,185,80,0.25)', color: 'var(--success)', fontWeight: 600 }}>
        Cost: {fmtCost(usage.total_cost)}
      </span>
    </div>
  );
}