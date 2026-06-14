import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

type Config = Record<string, unknown>

interface FormSectionProps {
  title: string
  fields: Array<{
    key: string
    label: string
    type: 'text' | 'number' | 'boolean' | 'select'
    options?: string[]
    min?: number
    max?: number
  }>
  config: Config
  onChange: (key: string, value: unknown) => void
}

function FormSection({ title, fields, config, onChange }: FormSectionProps) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '20px 24px', marginBottom: 16,
    }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>{title}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 24px' }}>
        {fields.map(f => (
          <div key={f.key}>
            <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {f.label}
            </label>
            {f.type === 'boolean' ? (
              <div
                onClick={() => onChange(f.key, !config[f.key])}
                style={{
                  width: 36, height: 20, borderRadius: 10, cursor: 'pointer',
                  background: config[f.key] ? 'var(--accent)' : 'var(--bg-hover)',
                  position: 'relative', transition: 'background 0.2s',
                }}
              >
                <div style={{
                  width: 14, height: 14, borderRadius: '50%', background: '#fff',
                  position: 'absolute', top: 3,
                  left: config[f.key] ? 18 : 4,
                  transition: 'left 0.2s',
                }} />
              </div>
            ) : f.type === 'select' ? (
              <select
                value={String(config[f.key] ?? '')}
                onChange={e => onChange(f.key, e.target.value)}
                style={{
                  width: '100%', padding: '6px 10px', borderRadius: 6,
                  border: '1px solid var(--border)', background: 'var(--bg-main)',
                  color: 'var(--text-primary)', fontSize: 13,
                }}
              >
                {f.options?.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            ) : (
              <input
                type={f.type === 'number' ? 'number' : 'text'}
                value={String(config[f.key] ?? '')}
                min={f.min}
                max={f.max}
                onChange={e => onChange(f.key, f.type === 'number' ? Number(e.target.value) : e.target.value)}
                style={{
                  width: '100%', padding: '6px 10px', borderRadius: 6,
                  border: '1px solid var(--border)', background: 'var(--bg-main)',
                  color: 'var(--text-primary)', fontSize: 13, boxSizing: 'border-box',
                }}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  useEffect(() => {
    const t = setTimeout(() => closeRef.current(), 3000)
    return () => clearTimeout(t)
  }, [])

  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
      background: 'var(--success)', color: '#fff', padding: '12px 20px',
      borderRadius: 8, fontSize: 13, fontWeight: 600,
      boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
      animation: 'fadeUp 0.2s ease',
    }}>
      {message}
    </div>
  )
}

const SECTIONS = [
  {
    title: 'LLM Configuration',
    fields: [
      { key: 'llm_primary', label: 'Primary Model', type: 'text' as const },
      { key: 'llm_fallback', label: 'Fallback Model', type: 'text' as const },
      { key: 'llm_cost_model', label: 'Cost Estimation Model', type: 'text' as const },
      { key: 'llm_timeout_seconds', label: 'Timeout (seconds)', type: 'number' as const, min: 5, max: 120 },
      { key: 'llm_max_retries', label: 'Max Retries', type: 'number' as const, min: 0, max: 10 },
    ],
  },
  {
    title: 'Validation & Safety',
    fields: [
      { key: 'validation_risk_threshold', label: 'Risk Threshold (0-100)', type: 'number' as const, min: 0, max: 100 },
      { key: 'auto_approve_enabled', label: 'Auto-Approve', type: 'boolean' as const },
      { key: 'circuit_breaker_failures', label: 'Circuit Breaker Failures', type: 'number' as const, min: 1, max: 20 },
      { key: 'circuit_breaker_window_seconds', label: 'Circuit Breaker Window (s)', type: 'number' as const, min: 10, max: 600 },
      { key: 'max_variants_per_query', label: 'Max Variants per Query', type: 'number' as const, min: 1, max: 10 },
      { key: 'min_confidence_for_approve', label: 'Min Confidence Level', type: 'select' as const, options: ['LOW', 'MEDIUM', 'HIGH'] },
    ],
  },
  {
    title: 'A/B Testing',
    fields: [
      { key: 'ab_test_default_traffic_split', label: 'Default Traffic Split (%)', type: 'number' as const, min: 0, max: 50 },
      { key: 'ab_test_shadow_duration_hours', label: 'Shadow Duration (hours)', type: 'number' as const, min: 1, max: 168 },
      { key: 'ab_test_min_executions', label: 'Min Executions for Significance', type: 'number' as const, min: 10, max: 10000 },
      { key: 'ab_test_p_value_threshold', label: 'P-Value Threshold', type: 'number' as const, min: 0.01, max: 0.1 },
      { key: 'ab_test_auto_promote_enabled', label: 'Auto-Promote on Significance', type: 'boolean' as const },
    ],
  },
  {
    title: 'Snowflake & Retention',
    fields: [
      { key: 'snowflake_poll_interval_seconds', label: 'Poll Interval (seconds)', type: 'number' as const, min: 60, max: 3600 },
      { key: 'snowflake_query_history_days', label: 'Query History (days)', type: 'number' as const, min: 1, max: 90 },
      { key: 'snowflake_max_queries_per_poll', label: 'Max Queries per Poll', type: 'number' as const, min: 10, max: 5000 },
      { key: 'query_retention_days', label: 'Query Retention (days)', type: 'number' as const, min: 7, max: 365 },
      { key: 'optimization_retention_days', label: 'Optimization Retention (days)', type: 'number' as const, min: 30, max: 1825 },
    ],
  },
  {
    title: 'Standardization',
    fields: [
      { key: 'standardization_enabled', label: 'Enable Standardization', type: 'boolean' as const },
      { key: 'standardization_enforcement_level', label: 'Enforcement Level', type: 'select' as const, options: ['passive', 'advisory', 'enforced'] },
      { key: 'keyword_uppercase_enabled', label: 'Keyword Uppercase', type: 'boolean' as const },
      { key: 'cte_suggestion_enabled', label: 'CTE Suggestions', type: 'boolean' as const },
      { key: 'max_query_length_chars', label: 'Max Query Length (chars)', type: 'number' as const, min: 1000, max: 100000 },
    ],
  },
]

export function AdminPanel() {
  const [config, setConfig] = useState<Config>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    api.get('/admin/config').then(r => {
      setConfig(r.data.config)
    }).finally(() => setLoading(false))
  }, [])

  const handleChange = (key: string, value: unknown) => {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await api.put('/admin/config', { config })
      setConfig(r.data.config)
      setToast('Configuration saved')
    } catch {
      setToast('Save failed — check console')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 28, color: 'var(--text-muted)', fontSize: 13 }}>Loading config…</div>
    )
  }

  return (
    <div style={{ padding: 28, maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>Admin Panel</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Live configuration — changes take effect immediately</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: '8px 20px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 600,
            opacity: saving ? 0.7 : 1,
          }}
        >
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>

      {SECTIONS.map(section => (
        <FormSection
          key={section.title}
          title={section.title}
          fields={section.fields}
          config={config}
          onChange={handleChange}
        />
      ))}

      {toast && <Toast message={toast} onClose={() => setToast(null)} />}
    </div>
  )
}
