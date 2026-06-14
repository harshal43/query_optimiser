import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'

export interface Toast {
  id: string
  message: string
  type: 'success' | 'info' | 'warning' | 'error'
}

interface ToastsState {
  items: Toast[]
}

export const toastsSlice = createSlice({
  name: 'toasts',
  initialState: { items: [] } as ToastsState,
  reducers: {
    addToast(state, action: PayloadAction<Omit<Toast, 'id'>>) {
      const id = Date.now().toString()
      state.items.push({ id, ...action.payload })
      if (state.items.length > 3) state.items.shift()
    },
    removeToast(state, action: PayloadAction<string>) {
      state.items = state.items.filter(t => t.id !== action.payload)
    },
  },
})

export const { addToast, removeToast } = toastsSlice.actions
