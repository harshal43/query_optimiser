import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Query, Optimization } from '../types'
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

const FINDING_COLORS: Record<string, { bg: string; border: string; dot: string }> = {
  certain:    { bg: 'rgba(239,68,68,0.07)',  border: 'rgba(239,68,68,0.25)',  dot: 'var(--danger)' },
  probable:   { bg: 'rgba(245,158,11,0.07)', border: 'rgba(245,158,11,0.25)', dot: '#f59e0b' },
  speculative:{ bg: 'rgba(99,102,241,0.07)', border: 'rgba(99,102,241,0.25)', dot: '#6366f1' },
}

interface Finding {
  type: string
  message: string
  [key: string]: unknown
}

interface Variant {
  id: string
  label: string
  sql: string
  techniques: string[]
  rationale?: string
  source?: string
}

function FindingRow({ finding, level }: { finding: Finding; level: 'certain' | 'probable' | 'speculative' }) {
  const c = FINDING_COLORS[level]
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 10px', background: c.bg, border: `1px solid ${c.border}`, borderRadius: 6, marginBottom: 6 }}>
      <div style={{ width: 7, height: 7, borderRadius: '50%', background: c.dot, marginTop: 5, flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.5 }}>{finding.message}</div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{finding.type.replace(/_/g, ' ')}</div>
      </div>
    </div>
  )
}

function DiagnosisSection({ diagnosis }: { diagnosis: Record<string, unknown> }) {
  const certain     = (diagnosis.certain     as Finding[] | undefined) ?? []
  const probable    = (diagnosis.probable    as Finding[] | undefined) ?? []
  const speculative = (diagnosis.speculative as Finding[] | undefined) ?? []
  const llmEnriched = Boolean(diagnosis.llm_enriched)
  const total = certain.length + probable.length + speculative.length

  if (total === 0) {
    return <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' }}>No issues detected by analysis.</div>
  }

  return (
    <div>
      {llmEnriched && (
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 10, color: '#6366f1', background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)', borderRadius: 4, padding: '2px 8px', marginBottom: 12 }}>
          <span>✦</span> AI-enriched diagnosis
        </div>
      )}

      {certain.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--danger)', marginBottom: 6 }}>
            Certain ({certain.length})
          </div>
          {certain.map((f, i) => <FindingRow key={i} finding={f} level="certain" />)}
        </div>
      )}

      {probable.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#f59e0b', marginBottom: 6 }}>
            Probable ({probable.length})
          </div>
          {probable.map((f, i) => <FindingRow key={i} finding={f} level="probable" />)}
        </div>
      )}

      {speculative.length > 0 && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#6366f1', marginBottom: 6 }}>
            Speculative ({speculative.length})
          </div>
          {speculative.map((f, i) => <FindingRow key={i} finding={f} level="speculative" />)}
        </div>
      )}
    </div>
  )
}

function VariantCard({ variant, recommended }: { variant: Variant; recommended: string | null }) {
  const [expanded, setExpanded] = useState(variant.id === recommended)
  const isRec = variant.id === recommended

  return (
    <div style={{ border: `1px solid ${isRec ? 'var(--accent)' : 'var(--border)'}`, borderRadius: 8, marginBottom: 10, overflow: 'hidden' }}>
      <div
        onClick={() => setExpanded(e => !e)}
        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', cursor: 'pointer', background: isRec ? 'rgba(99,102,241,0.05)' : 'var(--bg-card)' }}
      >
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{variant.label}</span>
        {isRec && <span style={{ fontSize: 10, color: 'var(--accent)', background: 'rgba(99,102,241,0.12)', padding: '1px 6px', borderRadius: 3, fontWeight: 700 }}>RECOMMENDED</span>}
        {variant.source === 'llm' && <span style={{ fontSize: 10, color: '#6366f1', background: 'rgba(99,102,241,0.1)', padding: '1px 6px', borderRadius: 3 }}>AI</span>}
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div style={{ padding: '0 14px 14px' }}>
          {variant.rationale && (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
              {variant.rationale}
            </div>
          )}
          {variant.techniques?.length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
              {variant.techniques.map(t => (
                <span key={t} style={{ fontSize: 10, color: 'var(--text-muted)', background: 'var(--bg-hover)', padding: '2px 7px', borderRadius: 4 }}>
                  {t.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          )}
          <SQLBlock sql={variant.sql} />
        </div>
      )}
    </div>
  )
}

function CostPredictions({ cost }: { cost: Record<string, unknown> }) {
  const variants = (cost.variants as Array<Record<string, unknown>> | undefined) ?? []
  if (variants.length === 0) return null

  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 18px', marginBottom: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 12 }}>Cost Predictions</div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {variants.map((v, i) => {
          const savingsPct  = Number(v.savings_pct  ?? 0)
          const savingsCred = Number(v.savings_credits ?? 0)
          return (
            <div key={i} style={{ flex: 1, minWidth: 120, background: 'var(--bg-hover)', borderRadius: 6, padding: '10px 12px' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>{String(v.variant_id ?? `v${i + 1}`)}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--success)' }}>{savingsPct.toFixed(0)}%</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{savingsCred.toFixed(2)} credits saved</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ValidationResults({ validation }: { validation: Record<string, unknown> }) {
  const riskScore = Number(validation.risk_score ?? 0)
  const riskLevel = String(validation.risk_level ?? '')
  const checks    = (validation.checks as Record<string, boolean> | undefined) ?? {}
  const checkCount = Object.keys(checks).length

  if (!riskLevel && checkCount === 0) return null

  const riskColor = riskScore >= 70 ? 'var(--danger)' : riskScore >= 40 ? '#f59e0b' : 'var(--success)'

  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 18px', marginBottom: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 12 }}>Validation</div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        {riskLevel && (
          <div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>Risk</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: riskColor }}>{riskLevel.toUpperCase()} {riskScore > 0 ? `(${riskScore})` : ''}</div>
          </div>
        )}
        {checkCount > 0 && (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {Object.entries(checks).map(([k, v]) => (
              <span key={k} style={{ fontSize: 10, padding: '2px 7px', borderRadius: 4, background: v ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', color: v ? 'var(--success)' : 'var(--danger)', border: `1px solid ${v ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}` }}>
                {v ? '✓' : '✗'} {k.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function QueryDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [query, setQuery]               = useState<Query | null>(null)
  const [optimization, setOptimization] = useState<Optimization | null>(null)
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      api.get(`/queries/${id}`),
      api.get(`/optimizations?query_id=${id}&limit=1`),
    ])
      .then(([qRes, oRes]) => {
        setQuery(qRes.data)
        const items = oRes.data?.items ?? []
        if (items.length > 0) setOptimization(items[0])
      })
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
  const execMs       = Number(m.execution_time_ms ?? 0)
  const credits      = Number(m.credits_used ?? 0)
  const bytesScanned = Number(m.bytes_scanned ?? 0)
  const bytesSpilled = Number(m.bytes_spilled_remote ?? 0)
  const rows         = Number(m.rows_produced ?? 0)

  const diagnosis    = optimization?.diagnosis ?? {}
  const variants     = (optimization?.variants ?? []) as Variant[]
  const costPred     = optimization?.cost_predictions ?? {}
  const validation   = optimization?.validation_results ?? {}
  const recommended  = optimization?.recommended_variant ?? null

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
        <MetricCard label="Exec Time"     value={execMs       ? fmtMs(execMs)          : '—'} />
        <MetricCard label="Credits"       value={credits      ? credits.toFixed(3)      : '—'} />
        <MetricCard label="Bytes Scanned" value={bytesScanned ? fmtBytes(bytesScanned) : '—'} />
        <MetricCard label="Remote Spill"  value={bytesSpilled ? fmtBytes(bytesSpilled) : 'None'} sub={bytesSpilled > 0 ? 'Performance issue' : undefined} />
        <MetricCard label="Rows"          value={rows         ? rows.toLocaleString()  : '—'} />
      </div>

      {/* SQL */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 8 }}>Original Query</div>
        <SQLBlock sql={query.query_text} />
      </div>

      {/* Agent Diagnosis */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 18px', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>Agent Diagnosis</div>
          {query.classification && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-hover)', padding: '2px 8px', borderRadius: 4 }}>
              {query.classification}
            </span>
          )}
          {optimization && (
            <span style={{ fontSize: 10, color: 'var(--success)', marginLeft: 'auto' }}>
              ● {optimization.status.replace(/_/g, ' ')}
            </span>
          )}
        </div>

        {optimization ? (
          <DiagnosisSection diagnosis={diagnosis} />
        ) : (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' }}>
            No optimization run yet.
            <button
              onClick={() => api.post('/optimizations', { query_id: query.query_id }).then(r => {
                api.get(`/optimizations/${r.data.optimization_id}`).then(or => setOptimization(or.data))
              })}
              style={{ marginLeft: 10, fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
            >
              Run now
            </button>
          </div>
        )}
      </div>

      {/* Cost Predictions */}
      {optimization && <CostPredictions cost={costPred} />}

      {/* Validation */}
      {optimization && <ValidationResults validation={validation} />}

      {/* Variants */}
      {variants.length > 0 && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 18px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 12 }}>
            Optimized Variants ({variants.length})
          </div>
          {variants.map(v => (
            <VariantCard key={v.id} variant={v} recommended={recommended} />
          ))}
        </div>
      )}
    </div>
  )
}
