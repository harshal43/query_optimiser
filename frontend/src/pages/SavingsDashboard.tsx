import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '../api/client'

interface Summary {
  total_credits_saved: number
  total_optimizations: number
  avg_savings_pct: number
  total_queries: number
}

interface MonthData { month: string; credits_saved: number; optimization_count: number }
interface TeamData { team_name: string; credits_saved: number; optimization_count: number }
interface TechData { name: string; category: string; success_rate: number; failure_rate: number; application_count: number }

function MetricCard({ label, value, unit, color }: { label: string; value: string | number; unit?: string; color: string }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8,
      padding: '18px 22px', flex: 1,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 800, color }}>
        {value}{unit && <span style={{ fontSize: 14, fontWeight: 500, marginLeft: 4 }}>{unit}</span>}
      </div>
    </div>
  )
}

function TeamBar({ name, value, max }: { name: string; value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
        <span style={{ color: 'var(--text-primary)' }}>{name}</span>
        <span style={{ color: 'var(--text-muted)', fontFamily: 'monospace' }}>{value.toFixed(1)} cr</span>
      </div>
      <div style={{ height: 6, background: 'var(--bg-hover)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', borderRadius: 3 }} />
      </div>
    </div>
  )
}

export function SavingsDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [monthly, setMonthly] = useState<MonthData[]>([])
  const [byTeam, setByTeam] = useState<TeamData[]>([])
  const [techniques, setTechniques] = useState<TechData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/analytics/savings'),
      api.get('/analytics/patterns'),
    ]).then(([sR, pR]) => {
      setSummary(sR.data.summary)
      setMonthly(sR.data.monthly)
      setByTeam(sR.data.by_team)
      setTechniques(pR.data.techniques)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ padding: 28, color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>

  const maxTeamCredits = Math.max(...byTeam.map(t => t.credits_saved), 0.1)

  return (
    <div style={{ padding: 28, maxWidth: 1100 }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>Savings Dashboard</h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Aggregated credit savings and optimization effectiveness</p>
      </div>

      {/* Metric cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 28 }}>
        <MetricCard label="Total Credits Saved" value={summary?.total_credits_saved.toFixed(1) ?? '0'} unit="cr" color="var(--success)" />
        <MetricCard label="Optimizations" value={summary?.total_optimizations ?? 0} color="var(--accent)" />
        <MetricCard label="Avg Savings" value={summary?.avg_savings_pct.toFixed(1) ?? '0'} unit="%" color="var(--warning)" />
        <MetricCard label="Queries Analyzed" value={summary?.total_queries ?? 0} color="var(--text-primary)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, marginBottom: 20 }}>
        {/* Monthly chart */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 20px 12px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>Monthly Credit Savings</div>
          {monthly.length === 0 ? (
            <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
              No approved optimizations yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={monthly} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }}
                  formatter={(v: number) => [`${v.toFixed(2)} credits`, 'Saved']}
                />
                <Bar dataKey="credits_saved" fill="var(--accent)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Team breakdown */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>By Team</div>
          {byTeam.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No team data yet</div>
          ) : (
            byTeam.map(t => <TeamBar key={t.team_name} name={t.team_name} value={t.credits_saved} max={maxTeamCredits} />)
          )}
        </div>
      </div>

      {/* Technique grid */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 14 }}>Technique Effectiveness</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {['Technique', 'Category', 'Success Rate', 'Failure Rate', 'Applied'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 12px', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {techniques.map(t => (
              <tr key={t.name} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 12px', color: 'var(--text-primary)', fontWeight: 600 }}>{t.name}</td>
                <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{t.category}</td>
                <td style={{ padding: '10px 12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 60, height: 4, background: 'var(--bg-hover)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ width: `${t.success_rate * 100}%`, height: '100%', background: 'var(--success)', borderRadius: 2 }} />
                    </div>
                    <span style={{ color: 'var(--success)', fontFamily: 'monospace', fontSize: 11 }}>{(t.success_rate * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--danger)', fontFamily: 'monospace', fontSize: 11 }}>{(t.failure_rate * 100).toFixed(0)}%</td>
                <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{t.application_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
