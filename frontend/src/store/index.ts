import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authSlice';
import requestsReducer from './requestsSlice';
import feedbackReducer from './feedbackSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    requests: requestsReducer,
    feedback: feedbackReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
