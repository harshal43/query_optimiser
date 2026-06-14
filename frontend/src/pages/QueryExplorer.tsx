import type React from 'react'
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Query } from '../types'

const SEV_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  critical: { bg: 'var(--danger-bg)',     color: 'var(--danger)',           label: 'Critical' },
  high:     { bg: 'var(--badge-high-bg)', color: 'var(--badge-high-color)', label: 'High' },
  medium:   { bg: 'var(--badge-med-bg)',  color: 'var(--badge-med-color)',  label: 'Medium' },
  low:      { bg: 'var(--success-bg)',    color: 'var(--success)',           label: 'Low' },
}

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  pending_review: { bg: 'var(--warning-bg)',   color: 'var(--warning)' },
  approved:       { bg: 'var(--success-bg)',   color: 'var(--success)' },
  rejected:       { bg: 'var(--danger-bg)',    color: 'var(--danger)'  },
  ab_testing:     { bg: 'var(--accent-light)', color: 'var(--accent)'  },
}

function Badge({ value, map }: {
  value: string | null
  map: Record<string, { bg: string; color: string; label?: string }>
}) {
  if (!value) return <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>—</span>
  const s = map[value] ?? { bg: 'var(--bg-hover)', color: 'var(--text-secondary)' }
  return (
    <span style={{ background: s.bg, color: s.color, padding: '2px 7px', borderRadius: 20, fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>
      {(s as { label?: string }).label ?? value.replace(/_/g, ' ')}
    </span>
  )
}

function fmt(d: string) {
  const diff = Date.now() - new Date(d).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return `${Math.floor(diff / 60_000)}m ago`
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const TH: React.CSSProperties = {
  padding: '9px 12px', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em',
  borderBottom: '1px solid var(--border)', background: 'var(--bg-app)',
  position: 'sticky', top: 0, zIndex: 1,
}
const TD: React.CSSProperties = {
  padding: '9px 12px', fontSize: 12, color: 'var(--text-primary)',
  borderBottom: '1px solid var(--border)', verticalAlign: 'middle',
}

const LIMIT = 50

export function QueryExplorer() {
  const navigate = useNavigate()
  const [items, setItems] = useState<Query[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)

  const load = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) })
    if (severity) params.set('severity', severity)
    if (status) params.set('status', status)
    api.get(`/queries?${params}`)
      .then(r => { setItems(r.data.items); setTotal(r.data.total); setError(null) })
      .catch(() => setError('Failed to load queries'))
      .finally(() => setLoading(false))
  }, [offset, severity, status])

  useEffect(() => { load() }, [load])

  const filtered = search
    ? items.filter(q => q.query_preview?.toLowerCase().includes(search.toLowerCase()))
    : items

  const credits = (q: Query) => {
    const c = q.execution_metrics?.credits_used
    return c != null ? Number(c).toFixed(2) : '—'
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Toolbar */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0, background: 'var(--bg-card)' }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search queries…"
          style={{ flex: 1, maxWidth: 340, padding: '6px 10px', background: 'var(--input-bg)', border: '1px solid var(--input-border)', borderRadius: 5, color: 'var(--text-primary)', fontSize: 13 }}
        />
        <select value={severity} onChange={e => { setSeverity(e.target.value); setOffset(0) }}
          style={{ padding: '6px 10px', background: 'var(--input-bg)', border: '1px solid var(--input-border)', borderRadius: 5, color: 'var(--text-primary)', fontSize: 13 }}>
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select value={status} onChange={e => { setStatus(e.target.value); setOffset(0) }}
          style={{ padding: '6px 10px', background: 'var(--input-bg)', border: '1px solid var(--input-border)', borderRadius: 5, color: 'var(--text-primary)', fontSize: 13 }}>
          <option value="">All statuses</option>
          <option value="pending_review">Pending Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="ab_testing">A/B Testing</option>
        </select>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>{total} queries</span>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {error && <div style={{ padding: 20, color: 'var(--danger)' }}>{error}</div>}
        {loading && !items.length && <div style={{ padding: 20, color: 'var(--text-muted)' }}>Loading…</div>}
        {!loading && !filtered.length && !error && (
          <div style={{ padding: 28, color: 'var(--text-muted)' }}>No queries found.</div>
        )}
        {filtered.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Severity', 'Preview', 'Team', 'Warehouse', 'Credits', 'Status', 'When'].map(h => (
                  <th key={h} style={TH}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(q => (
                <tr key={q.query_id}
                  onClick={() => navigate(`/queries/${q.query_id}`)}
                  style={{ cursor: 'pointer', transition: 'background 0.1s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}>
                  <td style={TD}>
                    <Badge value={q.severity} map={SEV_COLORS} />
                  </td>
                  <td style={{ ...TD, maxWidth: 320 }}>
                    <span style={{ color: 'var(--text-secondary)', fontFamily: 'monospace', fontSize: 11, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {q.query_preview ?? '—'}
                    </span>
                  </td>
                  <td style={TD}><span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{q.team_id ? q.team_id.slice(0, 8) + '…' : '—'}</span></td>
                  <td style={TD}>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                      {q.warehouse ?? '—'}
                      {q.warehouse_size && <><br/><span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{q.warehouse_size}</span></>}
                    </span>
                  </td>
                  <td style={{ ...TD, textAlign: 'right', fontFamily: 'monospace', fontSize: 12 }}>{credits(q)}</td>
                  <td style={TD}><Badge value={q.status} map={STATUS_COLORS} /></td>
                  <td style={{ ...TD, color: 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>{fmt(q.ingestion_timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > LIMIT && (
        <div style={{ padding: '10px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0, background: 'var(--bg-card)' }}>
          <button onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}
            style={{ padding: '5px 12px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg-hover)', color: 'var(--text-primary)', cursor: offset === 0 ? 'not-allowed' : 'pointer', fontSize: 12 }}>
            ← Prev
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{offset + 1}–{Math.min(offset + LIMIT, total)} of {total}</span>
          <button onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= total}
            style={{ padding: '5px 12px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg-hover)', color: 'var(--text-primary)', cursor: offset + LIMIT >= total ? 'not-allowed' : 'pointer', fontSize: 12 }}>
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
