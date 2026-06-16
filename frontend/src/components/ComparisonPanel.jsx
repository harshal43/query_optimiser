// frontend/src/components/ComparisonPanel.jsx

function formatBytes(bytes) {
  if (bytes == null) return '—';
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(1)} KB`;
  return `${bytes} B`;
}

function formatMs(ms) {
  if (ms == null) return '—';
  if (ms >= 60000) return `${(ms / 60000).toFixed(1)} min`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
  return `${ms} ms`;
}

function formatNumber(n) {
  if (n == null) return '—';
  return n.toLocaleString();
}

function formatCredits(c) {
  if (c == null) return '—';
  return c.toFixed(4);
}

function ImprovementBadge({ pct }) {
  if (pct == null) return <span style={{ color: 'var(--text-dim)' }}>—</span>;
  const isGood = pct < 0;
  const color = isGood ? 'var(--success)' : '#f85149';
  const sign = pct > 0 ? '+' : '';
  return (
    <span style={{ color, fontWeight: 600, fontSize: 12 }}>
      {sign}{pct.toFixed(1)}%
    </span>
  );
}

export default function ComparisonPanel({ result, loading, onRerun }) {
  const thStyle = {
    padding: '8px 12px',
    fontSize: 11,
    color: 'var(--text-dim)',
    fontFamily: 'var(--sans)',
    textAlign: 'left',
    borderBottom: '1px solid var(--border)',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  };
  const tdStyle = {
    padding: '7px 12px',
    fontSize: 13,
    fontFamily: 'var(--font)',
    borderBottom: '1px solid var(--border)',
  };

  if (loading) {
    return (
      <div className="card" style={{ marginTop: 16 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '24px 0',
          }}
        >
          <span
            className="spinner"
            style={{
              width: 22,
              height: 22,
              borderWidth: 3,
              borderColor: 'rgba(88,166,255,0.2)',
              borderTopColor: 'var(--accent)',
            }}
          />
          <span
            style={{
              fontSize: 13,
              color: 'var(--text-dim)',
              fontFamily: 'var(--sans)',
            }}
          >
            Running on Snowflake...
          </span>
        </div>
      </div>
    );
  }

  if (!result) return null;

  const { pre, post, improvement } = result;

  const rows = [
    {
      label: 'Elapsed time',
      pre: formatMs(pre.elapsed_ms),
      post: formatMs(post.elapsed_ms),
      imp: improvement?.elapsed_ms,
    },
    {
      label: 'Bytes scanned',
      pre: formatBytes(pre.bytes_scanned),
      post: formatBytes(post.bytes_scanned),
      imp: improvement?.bytes_scanned,
    },
    {
      label: 'Partitions scanned',
      pre:
        pre.partitions_scanned != null
          ? `${formatNumber(pre.partitions_scanned)} / ${formatNumber(pre.partitions_total)}`
          : '—',
      post:
        post.partitions_scanned != null
          ? `${formatNumber(post.partitions_scanned)} / ${formatNumber(post.partitions_total)}`
          : '—',
      imp: improvement?.partitions_scanned,
    },
    {
      label: 'Rows produced',
      pre: formatNumber(pre.rows_produced),
      post: formatNumber(post.rows_produced),
      imp: null,
    },
    {
      label: 'Credits used',
      pre: formatCredits(pre.credits),
      post: formatCredits(post.credits),
      imp: improvement?.credits,
    },
    {
      label: 'Spill (local)',
      pre: formatBytes(pre.bytes_spilled_local),
      post: formatBytes(post.bytes_spilled_local),
      imp: improvement?.bytes_spilled_local,
    },
  ];

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div
        className="card-title"
        style={{
          marginBottom: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          Snowflake Execution Comparison
          <span
            className="badge"
            style={{
              marginLeft: 8,
              background: 'rgba(88,166,255,0.1)',
              color: 'var(--accent)',
            }}
          >
            AGENT 4
          </span>
        </span>
        <button
          className="btn btn-secondary"
          style={{ fontSize: 12, padding: '2px 10px' }}
          onClick={onRerun}
        >
          &#9654; Re-run
        </button>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ ...thStyle, width: '35%' }}></th>
            <th style={thStyle}>Before</th>
            <th style={thStyle}>After</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td style={{ ...tdStyle, color: 'var(--text-dim)', fontSize: 12 }}>
                {row.label}
              </td>
              <td style={tdStyle}>{row.pre}</td>
              <td style={tdStyle}>{row.post}</td>
              <td style={{ ...tdStyle, textAlign: 'right' }}>
                <ImprovementBadge pct={row.imp} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div
        style={{
          marginTop: 10,
          fontSize: 11,
          color: 'var(--text-dim)',
          fontFamily: 'var(--sans)',
        }}
      >
        BEFORE = {pre.source === 'history' ? 'from query history' : 'live execution'}{' '}
        &middot; AFTER = live execution
        {(pre.error || post.error) && (
          <span style={{ color: '#f85149', marginLeft: 8 }}>
            {pre.error || post.error}
          </span>
        )}
      </div>
    </div>
  );
}
