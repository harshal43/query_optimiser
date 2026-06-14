import { createSlice } from '@reduxjs/toolkit'

interface SSEState {
  connected: boolean
  reconnects: number
  lastEventAt: string | null
}

const initialState: SSEState = { connected: false, reconnects: 0, lastEventAt: null }

export const sseSlice = createSlice({
  name: 'sse',
  initialState,
  reducers: {
    sseConnected(state) {
      state.connected = true
      state.lastEventAt = new Date().toISOString()
    },
    sseDisconnected(state) {
      state.connected = false
      state.reconnects += 1
    },
  },
})

export const { sseConnected, sseDisconnected } = sseSlice.actions
