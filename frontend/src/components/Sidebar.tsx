import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { useAppSelector } from '../store'

const PAGES = [
  { path: '/queries',  label: 'Query Explorer',    icon: 'search' },
  { path: '/review',   label: 'Review Queue',       icon: 'inbox',      badge: true },
  { path: '/ab-tests', label: 'A/B Test Console',   icon: 'flask' },
  { path: '/savings',  label: 'Savings Dashboard',  icon: 'trending-up' },
  { path: '/admin',    label: 'Admin Panel',         icon: 'settings' },
  { path: '/teams',    label: 'Team Config',         icon: 'users' },
]

const ICON_PATHS: Record<string, string[]> = {
  search:        ['M10 4a7 7 0 1 0 0 14A7 7 0 0 0 10 4z', 'M21 21l-4.35-4.35'],
  inbox:         ['M22 12h-6l-2 3H10l-2-3H2', 'M5.45 5.11A2 2 0 0 1 7.24 4h9.52a2 2 0 0 1 1.79 1.11L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z'],
  flask:         ['M9 3h6', 'M9 3v8l-5 10h16L15 11V3'],
  'trending-up': ['M23 6l-9.5 9.5-5-5L1 18', 'M17 6h6v6'],
  settings:      ['M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z', 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33A1.65 1.65 0 0 0 14 20.4V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'],
  users:         ['M17 20v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2', 'M9 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8', 'M23 20v-2a4 4 0 0 0-3-3.87', 'M16 4.13a4 4 0 0 1 0 7.75'],
  sun:           ['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M12 2v2', 'M12 20v2', 'M4.93 4.93l1.41 1.41', 'M17.66 17.66l1.41 1.41', 'M2 12h2', 'M20 12h2', 'M4.22 19.78l1.42-1.42', 'M18.36 5.64l1.42-1.42'],
  moon:          ['M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'],
}

function SvgIcon({ name, size = 15, color = 'currentColor' }: { name: string; size?: number; color?: string }) {
  const paths = ICON_PATHS[name] || ['M4 4h16v16H4z']
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      {paths.map((d, i) => <path key={i} d={d} />)}
    </svg>
  )
}

type HealthStatus = 'ok' | 'error' | 'unknown' | 'not_configured'

export function Sidebar({ pendingCount, isDark, onToggleDark }: {
  pendingCount: number
  isDark: boolean
  onToggleDark: () => void
}) {
  const navigate = useNavigate()
  const location = useLocation()
  const sseConnected = useAppSelector(s => s.sse.connected)
  const sseReconnects = useAppSelector(s => s.sse.reconnects)
  const [health, setHealth] = useState<Record<string, HealthStatus>>({
    DB: 'unknown', FAISS: 'unknown', Snowflake: 'unknown',
  })

  const checkHealth = () => {
    api.get('/health/ready').then((res) => {
      const c = res.data.checks
      setHealth({
        DB: c.db === 'ok' ? 'ok' : 'error',
        FAISS: c.faiss === 'ok' ? 'ok' : 'error',
        Snowflake: c.snowflake === 'not_configured' ? 'not_configured' : c.snowflake === 'ok' ? 'ok' : 'error',
      })
    }).catch(() => {
      setHealth({ DB: 'error', FAISS: 'error', Snowflake: 'error' })
    })
  }

  useEffect(() => {
    checkHealth()
    const id = setInterval(checkHealth, 30_000)
    return () => clearInterval(id)
  }, [])

  const isActive = (path: string) =>
    location.pathname === path || (path === '/queries' && location.pathname.startsWith('/queries/'))

  const dotColor = (s: HealthStatus) =>
    s === 'ok' ? 'var(--success)' : s === 'not_configured' ? 'var(--text-muted)' : s === 'unknown' ? 'var(--warning)' : 'var(--danger)'

  return (
    <nav style={{
      width: 220, flexShrink: 0, background: 'var(--bg-sidebar)',
      borderRight: '1px solid var(--sidebar-border)', display: 'flex',
      flexDirection: 'column', height: '100vh', position: 'sticky', top: 0, zIndex: 20,
    }}>
      <div style={{ padding: '17px 16px 14px', borderBottom: '1px solid var(--sidebar-border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 8l9-5 9 5-9 5-9-5z"/><path d="M3 16l9 5 9-5"/><path d="M3 12l9 5 9-5"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--sidebar-logo-text)', lineHeight: 1.2, letterSpacing: '-0.02em' }}>SQS</div>
            <div style={{ fontSize: 10, color: 'var(--sidebar-text)', opacity: 0.7 }}>Query Optimizer</div>
          </div>
        </div>
      </div>

      <div style={{ flex: 1, padding: '10px', overflowY: 'auto' }}>
        {PAGES.map((page) => (
          <div key={page.path} className={`nav-item${isActive(page.path) ? ' active' : ''}`} onClick={() => navigate(page.path)}>
            <SvgIcon name={page.icon} size={15} color={isActive(page.path) ? 'var(--nav-active-text)' : 'var(--sidebar-text)'} />
            <span style={{ flex: 1 }}>{page.label}</span>
            {page.badge && pendingCount > 0 && (
              <span style={{ background: 'var(--danger)', color: '#fff', borderRadius: 20, padding: '1px 6px', fontSize: 10, fontWeight: 700 }}>{pendingCount}</span>
            )}
          </div>
        ))}

        <div style={{ marginTop: 14, padding: '10px 12px', borderRadius: 6, background: 'var(--nav-hover)' }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--sidebar-text)', opacity: 0.6, marginBottom: 8 }}>System</div>
          {Object.entries(health).map(([label, status]) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--sidebar-text)', marginBottom: 5 }}>
              <div className={status === 'ok' ? 'live-dot' : ''} style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, background: dotColor(status) }} />
              {label}
            </div>
          ))}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--sidebar-text)', marginBottom: 5 }}>
            <div
              className={sseConnected ? 'live-dot' : ''}
              style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, background: sseConnected ? 'var(--success)' : 'var(--danger)' }}
            />
            SSE{sseReconnects > 0 ? ` (${sseReconnects}x)` : ''}
          </div>
        </div>
      </div>

      <div style={{ padding: '8px 10px', borderTop: '1px solid var(--sidebar-border)', flexShrink: 0 }}>
        <div onClick={onToggleDark} className="nav-item" style={{ marginBottom: 2 }}>
          <SvgIcon name={isDark ? 'sun' : 'moon'} size={15} color="var(--sidebar-text)" />
          <span>{isDark ? 'Light Mode' : 'Dark Mode'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#fff', flexShrink: 0 }}>U</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--sidebar-logo-text)', lineHeight: 1.2 }}>User</div>
            <div style={{ fontSize: 10, color: 'var(--sidebar-text)', opacity: 0.7 }}>Data Engineer</div>
          </div>
        </div>
      </div>
    </nav>
  )
}
