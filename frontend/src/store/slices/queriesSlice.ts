import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { Query } from '../../types'

interface QueriesState {
  items: Query[]
  loading: boolean
  error: string | null
}

const initialState: QueriesState = { items: [], loading: false, error: null }

export const queriesSlice = createSlice({
  name: 'queries',
  initialState,
  reducers: {
    setQueries(state, action: PayloadAction<Query[]>) {
      state.items = action.payload
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload
    },
    updateQueryStatus(state, action: PayloadAction<{ id: string; status: Query['status'] }>) {
      const q = state.items.find(q => q.query_id === action.payload.id)
      if (q) q.status = action.payload.status
    },
  },
})

export const { setQueries, setLoading, setError, updateQueryStatus } = queriesSlice.actions
