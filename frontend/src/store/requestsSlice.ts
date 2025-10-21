import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { Request } from '../types';

interface RequestsState {
  items: Request[];
  loading: boolean;
  error: string | null;
}

const initialState: RequestsState = {
  items: [],
  loading: false,
  error: null,
};

const requestsSlice = createSlice({
  name: 'requests',
  initialState,
  reducers: {
    setRequests: (state, action: PayloadAction<Request[]>) => {
      state.items = action.payload;
      state.loading = false;
    },
    addRequest: (state, action: PayloadAction<Request>) => {
      state.items.unshift(action.payload);
    },
    updateRequest: (state, action: PayloadAction<Request>) => {
      const index = state.items.findIndex(r => r.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = action.payload;
      }
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const { setRequests, addRequest, updateRequest, setLoading, setError } = requestsSlice.actions;
export default requestsSlice.reducer;
