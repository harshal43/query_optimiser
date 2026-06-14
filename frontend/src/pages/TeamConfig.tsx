import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Team } from '../types'

const ENFORCEMENT_OPTIONS = ['passive', 'advisory', 'enforced']
const WH_SIZES = ['X-Small', 'Small', 'Medium', 'Large', 'X-Large', '2X-Large', '3X-Large', '4X-Large']

interface TeamFormData {
  name: string
  warehouse: string
  warehouse_size: string
  enforcement_level: string
  ab_test_enabled: boolean
}

function TeamForm({ team, onSave, onCancel }: {
  team: Partial<Team> | null
  onSave: (data: TeamFormData) => Promise<void>
  onCancel: () => void
}) {
  const [form, setForm] = useState<TeamFormData>({
    name: team?.name ?? '',
    warehouse: team?.warehouse ?? 'COMPUTE_WH',
    warehouse_size: team?.warehouse_size ?? 'X-Small',
    enforcement_level: team?.enforcement_level ?? 'passive',
    ab_test_enabled: false,
  })
  const [saving, setSaving] = useState(false)

  const set = (key: keyof TeamFormData, value: string | boolean) =>
    setForm(prev => ({ ...prev, [key]: value }))

  const handleSubmit = async () => {
    if (!form.name.trim()) return
    setSaving(true)
    try { await onSave(form) } finally { setSaving(false) }
  }

  const inputStyle = {
    width: '100%', padding: '7px 10px', borderRadius: 6,
    border: '1px solid var(--border)', background: 'var(--bg-main)',
    color: 'var(--text-primary)', fontSize: 13, boxSizing: 'border-box' as const,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Team Name</label>
        <input style={inputStyle} value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Analytics Team" />
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Warehouse</label>
        <input style={inputStyle} value={form.warehouse} onChange={e => set('warehouse', e.target.value)} placeholder="COMPUTE_WH" />
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Warehouse Size</label>
        <select style={inputStyle} value={form.warehouse_size} onChange={e => set('warehouse_size', e.target.value)}>
          {WH_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Enforcement Level</label>
        <select style={inputStyle} value={form.enforcement_level} onChange={e => set('enforcement_level', e.target.value)}>
          {ENFORCEMENT_OPTIONS.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
        </select>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          onClick={() => set('ab_test_enabled', !form.ab_test_enabled)}
          style={{
            width: 36, height: 20, borderRadius: 10, cursor: 'pointer', flexShrink: 0,
            background: form.ab_test_enabled ? 'var(--accent)' : 'var(--bg-hover)',
            position: 'relative', transition: 'background 0.2s',
          }}
        >
          <div style={{
            width: 14, height: 14, borderRadius: '50%', background: '#fff',
            position: 'absolute', top: 3,
            left: form.ab_test_enabled ? 18 : 4,
            transition: 'left 0.2s',
          }} />
        </div>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Enable A/B Testing</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <button
          onClick={handleSubmit}
          disabled={saving || !form.name.trim()}
          style={{
            padding: '7px 18px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: 'var(--accent)', color: '#fff', fontSize: 12, fontWeight: 600,
            opacity: saving || !form.name.trim() ? 0.6 : 1,
          }}
        >
          {saving ? 'Saving…' : (team?.team_id ? 'Update' : 'Create')}
        </button>
        <button
          onClick={onCancel}
          style={{
            padding: '7px 14px', borderRadius: 6, border: '1px solid var(--border)',
            cursor: 'pointer', background: 'transparent', color: 'var(--text-secondary)', fontSize: 12,
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

function EnforcementBadge({ level }: { level: string }) {
  const colors: Record<string, string> = { passive: 'var(--text-muted)', advisory: 'var(--warning)', enforced: 'var(--danger)' }
  return (
    <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: colors[level] ?? 'var(--text-muted)' }}>
      {level}
    </span>
  )
}

export function TeamConfig() {
  const [teams, setTeams] = useState<Team[]>([])
  const [selected, setSelected] = useState<Team | null>(null)
  const [showNew, setShowNew] = useState(false)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = async () => {
    const r = await api.get('/teams')
    setTeams(r.data.items)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (data: { name: string; warehouse: string; warehouse_size: string; enforcement_level: string; ab_test_enabled: boolean }) => {
    await api.post('/teams', {
      name: data.name,
      warehouse: data.warehouse,
      warehouse_size: data.warehouse_size,
      enforcement_level: data.enforcement_level,
      ab_test_config: { enabled: data.ab_test_enabled },
    })
    setShowNew(false)
    load()
  }

  const handleUpdate = async (data: { name: string; warehouse: string; warehouse_size: string; enforcement_level: string; ab_test_enabled: boolean }) => {
    if (!selected) return
    await api.put(`/teams/${selected.team_id}`, {
      name: data.name,
      warehouse: data.warehouse,
      warehouse_size: data.warehouse_size,
      enforcement_level: data.enforcement_level,
      ab_test_config: { enabled: data.ab_test_enabled },
    })
    setSelected(null)
    load()
  }

  const handleDelete = async (teamId: string) => {
    setDeleting(teamId)
    try {
      await api.delete(`/teams/${teamId}`)
      if (selected?.team_id === teamId) setSelected(null)
      load()
    } finally { setDeleting(null) }
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Left panel */}
      <div style={{
        width: 280, borderRight: '1px solid var(--border)', background: 'var(--bg-card)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Teams ({teams.length})</span>
          <button
            onClick={() => { setShowNew(true); setSelected(null) }}
            style={{
              padding: '4px 10px', borderRadius: 5, border: 'none', cursor: 'pointer',
              background: 'var(--accent)', color: '#fff', fontSize: 11, fontWeight: 600,
            }}
          >+ New</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 12 }}>Loading…</div>
          ) : teams.length === 0 ? (
            <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 12 }}>No teams yet. Create one →</div>
          ) : (
            teams.map(team => (
              <div
                key={team.team_id}
                onClick={() => { setSelected(team); setShowNew(false) }}
                style={{
                  padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid var(--border)',
                  background: selected?.team_id === team.team_id ? 'var(--nav-hover)' : 'transparent',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>{team.name}</div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{team.warehouse}</span>
                  <EnforcementBadge level={team.enforcement_level} />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right panel */}
      <div style={{ flex: 1, padding: 28, overflowY: 'auto' }}>
        {showNew ? (
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20 }}>New Team</h3>
            <TeamForm team={null} onSave={handleCreate} onCancel={() => setShowNew(false)} />
          </div>
        ) : selected ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>{selected.name}</h3>
              <button
                onClick={() => handleDelete(selected.team_id)}
                disabled={deleting === selected.team_id}
                style={{
                  padding: '5px 12px', borderRadius: 5, border: '1px solid var(--danger)',
                  cursor: 'pointer', background: 'transparent', color: 'var(--danger)', fontSize: 11, fontWeight: 600,
                }}
              >
                {deleting === selected.team_id ? 'Deleting…' : 'Delete Team'}
              </button>
            </div>
            <TeamForm
              key={selected.team_id}
              team={selected}
              onSave={handleUpdate}
              onCancel={() => setSelected(null)}
            />
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: 13 }}>
            Select a team to edit, or create a new one
          </div>
        )}
      </div>
    </div>
  )
}
