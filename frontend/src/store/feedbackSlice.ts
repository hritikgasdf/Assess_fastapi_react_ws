import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { Feedback } from '../types';

interface FeedbackState {
  items: Feedback[];
  loading: boolean;
  error: string | null;
}

const initialState: FeedbackState = {
  items: [],
  loading: false,
  error: null,
};

const feedbackSlice = createSlice({
  name: 'feedback',
  initialState,
  reducers: {
    setFeedback: (state, action: PayloadAction<Feedback[]>) => {
      state.items = action.payload;
      state.loading = false;
    },
    addFeedback: (state, action: PayloadAction<Feedback>) => {
      state.items.unshift(action.payload);
    },
    updateFeedback: (state, action: PayloadAction<Feedback>) => {
      const index = state.items.findIndex(f => f.id === action.payload.id);
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

export const { setFeedback, addFeedback, updateFeedback, setLoading, setError } = feedbackSlice.actions;
export default feedbackSlice.reducer;
