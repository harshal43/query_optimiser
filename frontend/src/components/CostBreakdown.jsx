/** * Detailed token + cost table for both agents.
 *
 * Props:
 *   advisorUsage  : TokenUsage | null
 *   optimizerUsage: TokenUsage | null
 *   totalCost     : number | null
 */
export default function CostBreakdown({ advisorUsage, optimizerUsage, totalCost }) {
  if (!advisorUsage || !optimizerUsage) return null;

  const fmt = (n) => n.toLocaleString();
  const fmtCost = (v) => v < 0.0001 ? `$${v.toExponential(3)}` : `$${v.toFixed(7)}`;

  const rows = [
    { agent: 'Agent 1 - Advisor', usage: advisorUsage, color: 'var(--accent)', },
    { agent: 'Agent 2 - Optimizer', usage: optimizerUsage, color: 'var(--success)', },
  ];

  return (
    <div className="card">
      <div className="card-title">Cost Breakdown</div>
      <table className="cost-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>Prompt Tokens</th>
            <th>Completion Tokens</th>
            <th>Total Tokens</th>
            <th>Prompt Cost</th>
            <th>Completion Cost</th>
            <th>Agent Cost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ agent, usage, color }) => (
            <tr key={agent}>
              <td><span style={{ color, fontWeight: 600, fontSize: 12 }}>{agent}</span></td>
              <td><span className="cost-value">{fmt(usage.prompt_tokens)}</span></td>
              <td><span className="cost-value">{fmt(usage.completion_tokens)}</span></td>
              <td><span className="cost-value">{fmt(usage.total_tokens)}</span></td>
              <td><span className="cost-value">{fmtCost(usage.prompt_cost)}</span></td>
              <td><span className="cost-value">{fmtCost(usage.completion_cost)}</span></td>
              <td><span className="cost-value" style={{ fontWeight: 700, color }}>{fmtCost(usage.total_cost)}</span></td>
            </tr>
          ))}
          <tr className="total-row">
            <td colSpan={3}><strong>Total LLM Cost</strong></td>
            <td><span className="cost-value">{fmt(advisorUsage.total_tokens + optimizerUsage.total_tokens)}</span></td>
            <td><span className="cost-value">{fmtCost(advisorUsage.prompt_cost + optimizerUsage.prompt_cost)}</span></td>
            <td><span className="cost-value">{fmtCost(advisorUsage.completion_cost + optimizerUsage.completion_cost)}</span></td>
            <td><span className="cost-value" style={{ fontSize: 14 }}>{fmtCost(totalCost)}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}