import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { Optimization } from '../../types'

interface OptimizationsState {
  items: Optimization[]
  loading: boolean
  error: string | null
}

const initialState: OptimizationsState = { items: [], loading: false, error: null }

export const optimizationsSlice = createSlice({
  name: 'optimizations',
  initialState,
  reducers: {
    setOptimizations(state, action: PayloadAction<Optimization[]>) {
      state.items = action.payload
    },
    upsertOptimization(state, action: PayloadAction<Optimization>) {
      const idx = state.items.findIndex(o => o.optimization_id === action.payload.optimization_id)
      if (idx >= 0) state.items[idx] = action.payload
      else state.items.unshift(action.payload)
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload
    },
  },
})

export const { setOptimizations, upsertOptimization, setLoading } = optimizationsSlice.actions
