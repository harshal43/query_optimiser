import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { ABTest } from '../../types'

interface ABTestsState {
  items: ABTest[]
  loading: boolean
}

const initialState: ABTestsState = { items: [], loading: false }

export const abTestsSlice = createSlice({
  name: 'abTests',
  initialState,
  reducers: {
    setABTests(state, action: PayloadAction<ABTest[]>) {
      state.items = action.payload
    },
    upsertABTest(state, action: PayloadAction<ABTest>) {
      const idx = state.items.findIndex(t => t.test_id === action.payload.test_id)
      if (idx >= 0) state.items[idx] = action.payload
      else state.items.unshift(action.payload)
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload
    },
  },
})

export const { setABTests, upsertABTest, setLoading } = abTestsSlice.actions
