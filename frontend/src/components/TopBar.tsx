import { useLocation } from 'react-router-dom'
import { useAppSelector } from '../store'

const PAGE_TITLES: Record<string, string> = {
  '/queries':  'Query Explorer',
  '/review':   'Review Queue',
  '/ab-tests': 'A/B Test Console',
  '/savings':  'Savings Dashboard',
  '/admin':    'Admin Panel',
  '/teams':    'Team Config',
}

export function TopBar() {
  const location = useLocation()
  const isDetail = location.pathname.startsWith('/queries/')
  const title = isDetail ? 'Query Detail' : (PAGE_TITLES[location.pathname] ?? 'SQS')
  const connected = useAppSelector(s => s.sse.connected)

  return (
    <div style={{
      height: 50, borderBottom: '1px solid var(--border)', background: 'var(--bg-card)',
      display: 'flex', alignItems: 'center', paddingLeft: 24, paddingRight: 20,
      gap: 12, flexShrink: 0, zIndex: 10,
    }}>
      <h1 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>{title}</h1>
      <div style={{ flex: 1 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: connected ? 'var(--success)' : 'var(--text-muted)' }}>
        <div
          className={connected ? 'live-dot' : ''}
          style={{
            width: 7, height: 7, borderRadius: '50%',
            background: connected ? 'var(--success)' : 'var(--text-muted)',
          }}
        />
        {connected ? 'Live' : 'Connecting…'}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-hover)', padding: '3px 8px', borderRadius: 4, fontFamily: 'monospace' }}>
        PROD · SNOWFLAKE
      </div>
    </div>
  )
}
