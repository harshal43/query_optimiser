import { useEffect, useRef } from 'react'
import { useAppSelector, useAppDispatch } from '../store'
import { removeToast } from '../store/slices/toastsSlice'
import type { Toast } from '../store/slices/toastsSlice'

function ToastItem({ toast }: { toast: Toast }) {
  const dispatch = useAppDispatch()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    timerRef.current = setTimeout(() => dispatch(removeToast(toast.id)), 4000)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [])

  const colors: Record<string, string> = {
    success: 'var(--success)',
    info: 'var(--accent)',
    warning: 'var(--warning)',
    error: 'var(--danger)',
  }

  return (
    <div
      onClick={() => dispatch(removeToast(toast.id))}
      style={{
        background: colors[toast.type] ?? 'var(--accent)', color: '#fff',
        padding: '10px 16px', borderRadius: 7, fontSize: 12, fontWeight: 600,
        boxShadow: '0 4px 16px rgba(0,0,0,0.25)', cursor: 'pointer',
        animation: 'fadeUp 0.2s ease', maxWidth: 320,
      }}
    >
      {toast.message}
    </div>
  )
}

export function ToastContainer() {
  const toasts = useAppSelector(s => s.toasts.items)
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 2000,
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      {toasts.map(t => <ToastItem key={t.id} toast={t} />)}
    </div>
  )
}
