import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Query } from '../types'
import { SQLBlock } from '../utils/sqlHighlight'

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 16px', flex: 1, minWidth: 130 }}>
      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

function fmtMs(ms: number) {
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60_000).toFixed(1)}m`
}

function fmtBytes(b: number) {
  if (b < 1024) return `${b}B`
  if (b < 1024 ** 2) return `${(b / 1024).toFixed(1)}KB`
  if (b < 1024 ** 3) return `${(b / 1024 ** 2).toFixed(1)}MB`
  return `${(b / 1024 ** 3).toFixed(1)}GB`
}

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--danger)',
  high:     'var(--badge-high-color)',
  medium:   'var(--badge-med-color)',
  low:      'var(--success)',
}

export function QueryDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [query, setQuery] = useState<Query | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.get(`/queries/${id}`)
      .then(r => setQuery(r.data))
      .catch(() => setError('Query not found'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={{ padding: 28, color: 'var(--text-muted)' }}>Loading…</div>
  if (error || !query) return (
    <div style={{ padding: 28 }}>
      <div style={{ color: 'var(--danger)', marginBottom: 12 }}>{error ?? 'Not found'}</div>
      <button onClick={() => navigate('/queries')}
        style={{ padding: '6px 14px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--bg-hover)', color: 'var(--text-primary)', cursor: 'pointer', fontSize: 13 }}>
        ← Back to Explorer
      </button>
    </div>
  )

  const m = query.execution_metrics ?? {}
  const execMs        = Number(m.execution_time_ms ?? 0)
  const credits       = Number(m.credits_used ?? 0)
  const bytesScanned  = Number(m.bytes_scanned ?? 0)
  const bytesSpilled  = Number(m.bytes_spilled_remote ?? 0)
  const rows          = Number(m.rows_produced ?? 0)

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button onClick={() => navigate('/queries')}
          style={{ padding: '5px 10px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg-hover)', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>
          ← Back
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Query <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>{query.query_id.slice(0, 8)}…</span>
            </h2>
            {query.severity && (
              <span style={{ fontSize: 11, fontWeight: 700, color: SEV_COLOR[query.severity] ?? 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {query.severity}
              </span>
            )}
            {query.issue_type && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-hover)', padding: '2px 7px', borderRadius: 4 }}>
                {query.issue_type}
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
            {query.warehouse} · {query.warehouse_size} · {query.source}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <MetricCard label="Exec Time"     value={execMs       ? fmtMs(execMs)           : '—'} />
        <MetricCard label="Credits"       value={credits      ? credits.toFixed(3)       : '—'} />
        <MetricCard label="Bytes Scanned" value={bytesScanned  ? fmtBytes(bytesScanned)  : '—'} />
        <MetricCard label="Remote Spill"  value={bytesSpilled  ? fmtBytes(bytesSpilled)  : 'None'} sub={bytesSpilled > 0 ? 'Performance issue' : undefined} />
        <MetricCard label="Rows"          value={rows          ? rows.toLocaleString()   : '—'} />
      </div>

      {/* SQL */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 8 }}>Original Query</div>
        <SQLBlock sql={query.query_text} />
      </div>

      {/* Diagnosis */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 18px' }}>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 10 }}>Agent Diagnosis</div>
        {query.classification ? (
          <div>
            <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 6 }}>
              Classification: <strong>{query.classification}</strong>
            </div>
            {query.issue_type && <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Issue: {query.issue_type}</div>}
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10, padding: '8px 12px', background: 'var(--bg-hover)', borderRadius: 4 }}>
              Full multi-agent diagnosis available in Phase 2
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No classification — optimization not yet run. Available in Phase 2.</div>
        )}
      </div>
    </div>
  )
}
