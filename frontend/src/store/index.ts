import { configureStore } from '@reduxjs/toolkit'
import { useDispatch, useSelector } from 'react-redux'
import { queriesSlice } from './slices/queriesSlice'
import { optimizationsSlice } from './slices/optimizationsSlice'
import { abTestsSlice } from './slices/abTestsSlice'
import { teamsSlice } from './slices/teamsSlice'
import { sseSlice } from './slices/sseSlice'
import { toastsSlice } from './slices/toastsSlice'
import { sseMiddleware } from './middleware/sseMiddleware'

export const store = configureStore({
  reducer: {
    queries: queriesSlice.reducer,
    optimizations: optimizationsSlice.reducer,
    abTests: abTestsSlice.reducer,
    teams: teamsSlice.reducer,
    sse: sseSlice.reducer,
    toasts: toastsSlice.reducer,
  },
  middleware: (getDefault) => getDefault().concat(sseMiddleware),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector = <T>(selector: (state: RootState) => T) =>
  useSelector<RootState, T>(selector)
