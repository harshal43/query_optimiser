import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { SQLBlock } from '../utils/sqlHighlight'

interface VariantDetail {
  id: string
  label: string
  sql: string
  technique_details: Array<{ name: string; avg_credit_reduction_pct: number }>
}

interface OptimizationItem {
  optimization_id: string
  query_id: string
  diagnosis: {
    certain?: Array<{ type: string; message: string }>
    probable?: Array<{ type: string; message: string }>
    speculative?: Array<{ type: string; message: string }>
    primary_classification?: string
  }
  variants: VariantDetail[]
  cost_predictions: {
    original_credits?: number
    variants?: Array<{
      variant_id: string
      original_credits: number
      predicted_credits: number
      savings_pct: number
      confidence: string
      ci_lower: number
      ci_upper: number
      technique_attribution: Array<{ technique: string; credit_reduction_pct: number }>
    }>
  }
  validation_results: {
    overall_risk_score?: number
    gate_passed?: boolean
    variants?: Array<{
      variant_id: string
      checks: Array<{ name: string; result: string; detail: string }>
      risk_score: number
      passed: number
      warnings: number
      failures: number
    }>
  }
  recommended_variant: string | null
  status: string
  created_at: string
}

function Check({ name, result, detail }: { name: string; result: string; detail: string }) {
  const color = result === 'pass' ? 'var(--success)' : result === 'warn' ? 'var(--warning)' : 'var(--danger)'
  const icon = result === 'pass' ? '✓' : result === 'warn' ? '⚠' : '✕'
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 6 }}>
      <span style={{ color, fontWeight: 700, fontSize: 12, flexShrink: 0, width: 14 }}>{icon}</span>
      <div>
        <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>{name.replace(/_/g, ' ')}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{detail}</div>
      </div>
    </div>
  )
}

function RiskBar({ score }: { score: number }) {
  const color = score < 30 ? 'var(--success)' : score < 60 ? 'var(--warning)' : 'var(--danger)'
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Risk Score</span>
        <span style={{ fontSize: 12, fontWeight: 700, color }}>{score}/100</span>
      </div>
      <div style={{ height: 6, background: 'var(--border)', borderRadius: 3 }}>
        <div style={{ height: '100%', width: `${score}%`, background: color, borderRadius: 3, transition: 'width 0.4s' }} />
      </div>
    </div>
  )
}

export function ReviewQueue() {
  const [items, setItems] = useState<OptimizationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<OptimizationItem | null>(null)
  const [activeVariant, setActiveVariant] = useState<string>('v1')
  const [rejectModal, setRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [queryTexts, setQueryTexts] = useState<Record<string, string>>({})

  const load = () => {
    setLoading(true)
    api.get('/optimizations?status=pending_review')
      .then(r => {
        const fetched: OptimizationItem[] = r.data.items
        setItems(fetched)
        if (fetched.length > 0 && !selected) setSelected(fetched[0])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!selected) return
    setActiveVariant(selected.recommended_variant ?? 'v1')
    if (!queryTexts[selected.query_id]) {
      api.get(`/queries/${selected.query_id}`)
        .then(r => setQueryTexts(t => ({ ...t, [selected.query_id]: r.data.query_text })))
        .catch(() => {})
    }
  }, [selected?.optimization_id])

  const approve = async () => {
    if (!selected) return
    setActionLoading(true)
    try {
      await api.post(`/optimizations/${selected.optimization_id}/approve`, { selected_variant: activeVariant })
      setItems(i => i.filter(x => x.optimization_id !== selected.optimization_id))
      setSelected(null)
      load()
    } finally {
      setActionLoading(false)
    }
  }

  const reject = async () => {
    if (!selected || !rejectReason.trim()) return
    setActionLoading(true)
    try {
      await api.post(`/optimizations/${selected.optimization_id}/reject`, { reason: rejectReason })
      setRejectModal(false)
      setRejectReason('')
      setItems(i => i.filter(x => x.optimization_id !== selected.optimization_id))
      setSelected(null)
      load()
    } finally {
      setActionLoading(false)
    }
  }

  const variant = selected?.variants.find(v => v.id === activeVariant) ?? selected?.variants[0]
  const variantChecks = selected?.validation_results.variants?.find(v => v.variant_id === activeVariant)
  const costPred = selected?.cost_predictions.variants?.find(v => v.variant_id === activeVariant)
  const overallRisk = selected?.validation_results.overall_risk_score ?? 0

  if (loading) return <div style={{ padding: 28, color: 'var(--text-muted)' }}>Loading…</div>

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Left list */}
      <div style={{ width: 280, flexShrink: 0, borderRight: '1px solid var(--border)', overflowY: 'auto', background: 'var(--bg-sidebar)' }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--sidebar-text)' }}>
          Pending Review ({items.length})
        </div>

        {items.length === 0 && (
          <div style={{ padding: '20px 14px', fontSize: 12, color: 'var(--text-muted)' }}>
            No pending items. POST /api/optimizations with a query_id to generate one.
          </div>
        )}

        {items.map(item => {
          const classification = item.diagnosis.primary_classification ?? '—'
          const certain = item.diagnosis.certain?.length ?? 0
          const risk = item.validation_results.overall_risk_score ?? 0
          const isActive = selected?.optimization_id === item.optimization_id
          return (
            <div key={item.optimization_id}
              onClick={() => setSelected(item)}
              style={{
                padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid var(--border)',
                background: isActive ? 'var(--nav-active-bg)' : 'transparent',
                borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
              }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: isActive ? 'var(--nav-active-text)' : 'var(--sidebar-text)', marginBottom: 3 }}>
                {classification}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {certain} certain finding{certain !== 1 ? 's' : ''} · Risk {risk}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                {item.optimization_id.slice(0, 8)}…
              </div>
            </div>
          )
        })}
      </div>

      {/* Right detail panel */}
      {selected ? (
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {/* Variant tabs */}
          {selected.variants.length > 1 && (
            <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
              {selected.variants.map(v => (
                <button key={v.id} onClick={() => setActiveVariant(v.id)}
                  style={{
                    padding: '5px 12px', borderRadius: 4, border: '1px solid var(--border)', fontSize: 12, cursor: 'pointer',
                    background: activeVariant === v.id ? 'var(--accent)' : 'var(--bg-hover)',
                    color: activeVariant === v.id ? '#fff' : 'var(--text-primary)',
                  }}>
                  {v.label}
                </button>
              ))}
            </div>
          )}

          {/* Validation card */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 16px', marginBottom: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 10 }}>
              Validation Report
            </div>
            <RiskBar score={overallRisk} />
            {variantChecks?.checks.map(c => (
              <Check key={c.name} name={c.name} result={c.result} detail={c.detail} />
            ))}
          </div>

          {/* Cost prediction card */}
          {costPred && (
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 16px', marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 10 }}>
                Cost Prediction
              </div>
              <div style={{ display: 'flex', gap: 20, marginBottom: 10, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Before</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--danger)' }}>{costPred.original_credits.toFixed(3)} cr</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>→</div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>After</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--success)' }}>{costPred.predicted_credits.toFixed(3)} cr</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Savings</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--success)' }}>{costPred.savings_pct}%</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Confidence</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: costPred.confidence === 'HIGH' ? 'var(--success)' : 'var(--warning)' }}>
                    {costPred.confidence}
                  </div>
                </div>
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8 }}>
                95% CI: {costPred.ci_lower.toFixed(3)} – {costPred.ci_upper.toFixed(3)} credits
              </div>
              {costPred.technique_attribution.map(t => (
                <span key={t.technique} style={{ display: 'inline-block', fontSize: 10, background: 'var(--accent-light)', color: 'var(--accent)', borderRadius: 4, padding: '1px 6px', margin: '2px 4px 2px 0' }}>
                  {t.technique} −{t.credit_reduction_pct}%
                </span>
              ))}
            </div>
          )}

          {/* Diagnosis card */}
          {(selected.diagnosis.certain?.length || selected.diagnosis.probable?.length || selected.diagnosis.speculative?.length) ? (
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 16px', marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 10 }}>
                Diagnosis
              </div>
              {selected.diagnosis.certain?.map((f, i) => (
                <div key={i} style={{ marginBottom: 6, padding: '6px 10px', background: 'var(--danger-bg)', borderRadius: 4, borderLeft: '3px solid var(--danger)' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--danger)', textTransform: 'uppercase', marginBottom: 2 }}>Certain</div>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>{f.message}</div>
                </div>
              ))}
              {selected.diagnosis.probable?.map((f, i) => (
                <div key={i} style={{ marginBottom: 6, padding: '6px 10px', background: 'var(--warning-bg)', borderRadius: 4, borderLeft: '3px solid var(--warning)' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--warning)', textTransform: 'uppercase', marginBottom: 2 }}>Probable</div>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>{f.message}</div>
                </div>
              ))}
              {selected.diagnosis.speculative?.map((f, i) => (
                <div key={i} style={{ marginBottom: 6, padding: '6px 10px', background: 'var(--bg-hover)', borderRadius: 4, borderLeft: '3px solid var(--border)' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>Speculative</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f.message}</div>
                </div>
              ))}
            </div>
          ) : null}

          {/* SQL diff */}
          {variant && queryTexts[selected.query_id] && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 8 }}>SQL Diff</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>ORIGINAL</div>
                  <SQLBlock sql={queryTexts[selected.query_id]} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--success)', marginBottom: 4 }}>OPTIMIZED ({variant.label})</div>
                  <SQLBlock sql={variant.sql} style={{ borderColor: 'var(--success)' }} />
                </div>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 10, paddingTop: 8, paddingBottom: 24 }}>
            <button onClick={approve} disabled={actionLoading}
              style={{ padding: '9px 20px', borderRadius: 5, border: 'none', background: 'var(--success)', color: '#fff', fontWeight: 600, fontSize: 13, cursor: actionLoading ? 'not-allowed' : 'pointer', opacity: actionLoading ? 0.6 : 1 }}>
              Approve &amp; A/B Test
            </button>
            <button onClick={() => setRejectModal(true)} disabled={actionLoading}
              style={{ padding: '9px 20px', borderRadius: 5, border: '1px solid var(--danger)', background: 'transparent', color: 'var(--danger)', fontWeight: 600, fontSize: 13, cursor: actionLoading ? 'not-allowed' : 'pointer', opacity: actionLoading ? 0.6 : 1 }}>
              Reject &amp; Learn
            </button>
          </div>

          {/* Reject modal */}
          {rejectModal && (
            <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
              <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 24, width: 420 }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>Reject &amp; Learn</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>Your feedback trains the Pattern Learner agent to improve future optimizations.</div>
                <textarea
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  placeholder="Describe why this optimization is incorrect…"
                  rows={4}
                  style={{ width: '100%', padding: '8px 10px', background: 'var(--input-bg)', border: '1px solid var(--input-border)', borderRadius: 5, color: 'var(--text-primary)', fontSize: 13, resize: 'vertical', boxSizing: 'border-box' }}
                />
                <div style={{ display: 'flex', gap: 8, marginTop: 12, justifyContent: 'flex-end' }}>
                  <button onClick={() => { setRejectModal(false); setRejectReason('') }}
                    style={{ padding: '7px 14px', borderRadius: 4, border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-primary)', cursor: 'pointer', fontSize: 13 }}>
                    Cancel
                  </button>
                  <button onClick={reject} disabled={!rejectReason.trim() || actionLoading}
                    style={{ padding: '7px 14px', borderRadius: 4, border: 'none', background: 'var(--danger)', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600, opacity: !rejectReason.trim() ? 0.5 : 1 }}>
                    Reject
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
          Select an item from the queue
        </div>
      )}
    </div>
  )
}
