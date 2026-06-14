import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { Team } from '../../types'

interface TeamsState {
  items: Team[]
  loading: boolean
}

const initialState: TeamsState = { items: [], loading: false }

export const teamsSlice = createSlice({
  name: 'teams',
  initialState,
  reducers: {
    setTeams(state, action: PayloadAction<Team[]>) {
      state.items = action.payload
    },
    upsertTeam(state, action: PayloadAction<Team>) {
      const idx = state.items.findIndex(t => t.team_id === action.payload.team_id)
      if (idx >= 0) state.items[idx] = action.payload
      else state.items.push(action.payload)
    },
  },
})

export const { setTeams, upsertTeam } = teamsSlice.actions
