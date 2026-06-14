import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAppSelector, useAppDispatch } from '../store'
import { setABTests } from '../store/slices/abTestsSlice'
import type { ABTest } from '../types'

type Counts = { shadow: number; active: number; completed: number; rolled_back: number }

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    shadow: 'var(--text-muted)',
    active: 'var(--success)',
    completed: 'var(--accent)',
    rolled_back: 'var(--danger)',
  }
  const labels: Record<string, string> = {
    shadow: 'Shadow', active: 'Active', completed: 'Completed', rolled_back: 'Rolled Back',
  }
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
      color: '#fff', background: colors[status] ?? 'var(--text-muted)',
      padding: '2px 7px', borderRadius: 20,
    }}>
      {labels[status] ?? status}
    </span>
  )
}

function PValueBar({ value }: { value: number | null }) {
  if (value === null) return <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>—</span>
  const pct = Math.min(100, (1 - value) * 100)
  const color = value < 0.05 ? 'var(--success)' : value < 0.1 ? 'var(--warning)' : 'var(--danger)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--bg-hover)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, color, fontFamily: 'monospace', minWidth: 40 }}>{value.toFixed(3)}</span>
    </div>
  )
}

function TestRow({ test, onAction }: { test: ABTest; onAction: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)

  const promote = async () => {
    setLoading(true)
    try {
      await api.post(`/ab-tests/${test.test_id}/promote`, { traffic_pct: 10 })
      onAction()
    } catch (err) {
      console.error('promote failed', err)
    } finally { setLoading(false) }
  }

  const rollback = async () => {
    setLoading(true)
    try {
      await api.post(`/ab-tests/${test.test_id}/rollback`)
      onAction()
    } catch (err) {
      console.error('rollback failed', err)
    } finally { setLoading(false) }
  }

  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, marginBottom: 8, overflow: 'hidden' }}>
      <div
        onClick={() => setExpanded(e => !e)}
        style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
          cursor: 'pointer', background: 'var(--bg-card)',
        }}
      >
        <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-muted)', minWidth: 70 }}>
          {test.test_id.slice(0, 8)}
        </span>
        <StatusBadge status={test.status} />
        <span style={{ flex: 1, fontSize: 12, color: 'var(--text-secondary)' }}>
          Traffic: {test.traffic_split.control}% control / {test.traffic_split.optimized}% optimized
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {new Date(test.started_at).toLocaleDateString()}
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', background: 'var(--bg-main)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 6 }}>Control Metrics</div>
              {Object.keys(test.control_metrics).length === 0
                ? <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data yet</span>
                : Object.entries(test.control_metrics).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                    <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{String(v)}</span>
                  </div>
                ))
              }
            </div>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 6 }}>Variant Metrics</div>
              {Object.keys(test.variant_metrics).length === 0
                ? <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data yet</span>
                : Object.entries(test.variant_metrics).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                    <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{String(v)}</span>
                  </div>
                ))
              }
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 6 }}>Statistical Significance (p-value)</div>
            <PValueBar value={test.p_value} />
            {test.p_value !== null && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                {test.p_value < 0.05 ? 'Statistically significant (p < 0.05)' : 'Not yet significant'}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            {(test.status === 'shadow' || test.status === 'active') && (
              <button
                onClick={promote}
                disabled={loading}
                style={{
                  padding: '6px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
                  background: 'var(--accent)', color: '#fff', fontSize: 12, fontWeight: 600,
                }}
              >
                {test.status === 'shadow' ? 'Activate 10% Traffic' : 'Promote'}
              </button>
            )}
            {(test.status === 'shadow' || test.status === 'active') && (
              <button
                onClick={rollback}
                disabled={loading}
                style={{
                  padding: '6px 14px', borderRadius: 6, border: '1px solid var(--danger)', cursor: 'pointer',
                  background: 'transparent', color: 'var(--danger)', fontSize: 12, fontWeight: 600,
                }}
              >
                Rollback
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8,
      padding: '16px 20px', flex: 1,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{value}</div>
    </div>
  )
}

export function ABTestConsole() {
  const dispatch = useAppDispatch()
  const tests = useAppSelector(s => s.abTests.items)
  const [counts, setCounts] = useState<Counts>({ shadow: 0, active: 0, completed: 0, rolled_back: 0 })
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  const load = async () => {
    setLoading(true)
    try {
      const r = await api.get('/ab-tests')
      dispatch(setABTests(r.data.items))
      setCounts(r.data.counts)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'all' ? tests : tests.filter(t => t.status === filter)

  return (
    <div style={{ padding: 28, maxWidth: 1000 }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>A/B Test Console</h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Monitor and control optimization experiments</p>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <SummaryCard label="Active" value={counts.active} color="var(--success)" />
        <SummaryCard label="Shadow" value={counts.shadow} color="var(--warning)" />
        <SummaryCard label="Completed" value={counts.completed} color="var(--accent)" />
        <SummaryCard label="Rolled Back" value={counts.rolled_back} color="var(--danger)" />
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['all', 'shadow', 'active', 'completed', 'rolled_back'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '5px 12px', borderRadius: 20, border: '1px solid var(--border)',
              cursor: 'pointer', fontSize: 11, fontWeight: 600,
              background: filter === f ? 'var(--accent)' : 'var(--bg-card)',
              color: filter === f ? '#fff' : 'var(--text-secondary)',
            }}
          >
            {f === 'rolled_back' ? 'Rolled Back' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button
          onClick={load}
          style={{
            padding: '5px 12px', borderRadius: 6, border: '1px solid var(--border)',
            cursor: 'pointer', fontSize: 11, background: 'var(--bg-card)', color: 'var(--text-secondary)',
          }}
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
      ) : filtered.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
          No {filter === 'all' ? '' : filter} tests found. Approve an optimization in Review Queue to start a shadow test.
        </div>
      ) : (
        filtered.map(t => <TestRow key={t.test_id} test={t} onAction={load} />)
      )}
    </div>
  )
}
