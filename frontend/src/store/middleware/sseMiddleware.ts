import type { Middleware } from '@reduxjs/toolkit'
import { upsertOptimization } from '../slices/optimizationsSlice'
import { updateQueryStatus } from '../slices/queriesSlice'
import { upsertABTest } from '../slices/abTestsSlice'
import { sseConnected, sseDisconnected } from '../slices/sseSlice'
import { addToast } from '../slices/toastsSlice'

let eventSource: EventSource | null = null

export const sseMiddleware: Middleware = (store) => (next) => (action) => {
  const act = action as { type: string }

  if (act.type === 'sse/connect') {
    if (eventSource) eventSource.close()
    eventSource = new EventSource('/api/optimize/stream')

    eventSource.addEventListener('connected', () => {
      store.dispatch(sseConnected())
    })

    eventSource.addEventListener('review_required', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        if (data.event === 'optimization_approved') {
          store.dispatch(addToast({ message: 'Optimization approved — shadow test started', type: 'success' }))
        }
      } catch {}
    })

    eventSource.addEventListener('ab_test_promoted', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        const pct = data.traffic_split?.optimized ?? 10
        store.dispatch(addToast({ message: `A/B test promoted to ${pct}% traffic`, type: 'info' }))
      } catch {}
    })

    eventSource.addEventListener('ab_test_rolled_back', () => {
      store.dispatch(addToast({ message: 'A/B test rolled back to shadow mode', type: 'warning' }))
    })

    eventSource.addEventListener('ab_test_completed', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        const p = data.p_value != null ? ` (p=${Number(data.p_value).toFixed(3)})` : ''
        store.dispatch(addToast({ message: `A/B test completed${p}`, type: 'success' }))
      } catch {}
    })

    eventSource.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        switch (event.event) {
          case 'job_status_update':
            if (event.payload?.optimization) {
              store.dispatch(upsertOptimization(event.payload.optimization))
            }
            if (event.payload?.query_id && event.status) {
              store.dispatch(updateQueryStatus({ id: event.payload.query_id, status: event.status }))
            }
            break
          case 'ab_test_metric':
            if (event.payload?.ab_test) {
              store.dispatch(upsertABTest(event.payload.ab_test))
            }
            break
        }
      } catch {}
    }

    eventSource.onerror = () => {
      store.dispatch(sseDisconnected())
      eventSource?.close()
      eventSource = null
      setTimeout(() => store.dispatch({ type: 'sse/connect' }), 5000)
    }
  }

  if (act.type === 'sse/disconnect') {
    eventSource?.close()
    eventSource = null
    store.dispatch(sseDisconnected())
  }

  return next(action)
}
