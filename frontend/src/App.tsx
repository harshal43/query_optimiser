import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAppDispatch } from './store'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { ToastContainer } from './components/ToastContainer'
import { QueryExplorer } from './pages/QueryExplorer'
import { QueryDetail } from './pages/QueryDetail'
import { ReviewQueue } from './pages/ReviewQueue'
import { ABTestConsole } from './pages/ABTestConsole'
import { SavingsDashboard } from './pages/SavingsDashboard'
import { AdminPanel } from './pages/AdminPanel'
import { TeamConfig } from './pages/TeamConfig'

type Theme = 'frost' | 'depth'
const FLUID_ROUTES = ['/review', '/teams']

export default function App() {
  const dispatch = useAppDispatch()
  const [theme] = useState<Theme>(() => (localStorage.getItem('sqs-theme') as Theme) ?? 'frost')
  const [isDark, setIsDark] = useState(() => localStorage.getItem('sqs-dark') === 'true')
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    document.body.className = `${theme} ${isDark ? 'dark' : 'light'}`
  }, [theme, isDark])

  useEffect(() => {
    dispatch({ type: 'sse/connect' })
    return () => { dispatch({ type: 'sse/disconnect' }) }
  }, [dispatch])

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const toggleDark = () => {
    const next = !isDark
    setIsDark(next)
    localStorage.setItem('sqs-dark', String(next))
  }

  const isFluid = FLUID_ROUTES.includes(path)

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg-app)', color: 'var(--text-primary)', overflow: 'hidden' }}>
      <Sidebar pendingCount={0} isDark={isDark} onToggleDark={toggleDark} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        <TopBar />
        <div style={{ flex: 1, overflow: isFluid ? 'hidden' : 'auto' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/review" replace />} />
            <Route path="/queries" element={<QueryExplorer />} />
            <Route path="/queries/:id" element={<QueryDetail />} />
            <Route path="/review" element={<ReviewQueue />} />
            <Route path="/ab-tests" element={<ABTestConsole />} />
            <Route path="/savings" element={<SavingsDashboard />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/teams" element={<TeamConfig />} />
          </Routes>
          <ToastContainer />
        </div>
      </div>
    </div>
  )
}
