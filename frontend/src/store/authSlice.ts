import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import api from '../services/api';
import type { User, LoginCredentials, RegisterData, AuthResponse } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: false,
  loading: false,
  error: null,
};

export const login = createAsyncThunk(
  'auth/login',
  async (credentials: LoginCredentials, { rejectWithValue }) => {
    try {
      const response = await api.post<AuthResponse>('/api/auth/login', credentials);
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      
      const userResponse = await api.get<User>('/api/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      
      return { token: access_token, user: userResponse.data };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Login failed');
    }
  }
);

export const register = createAsyncThunk(
  'auth/register',
  async (data: RegisterData, { rejectWithValue }) => {
    try {
      const response = await api.post<User>('/api/auth/register', data);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Registration failed');
    }
  }
);

export const checkAuth = createAsyncThunk(
  'auth/checkAuth',
  async (_, { rejectWithValue }) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        return rejectWithValue('No token found');
      }
      
      const userResponse = await api.get<User>('/api/auth/me');
      return { token, user: userResponse.data };
    } catch (error: any) {
      localStorage.removeItem('token');
      return rejectWithValue(error.response?.data?.detail || 'Authentication failed');
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      localStorage.removeItem('token');
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false;
        state.isAuthenticated = true;
        state.token = action.payload.token;
        state.user = action.payload.user;
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(register.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(register.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(register.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(checkAuth.pending, (state) => {
        state.loading = true;
      })
      .addCase(checkAuth.fulfilled, (state, action) => {
        state.loading = false;
        state.isAuthenticated = true;
        state.token = action.payload.token;
        state.user = action.payload.user;
      })
      .addCase(checkAuth.rejected, (state) => {
        state.loading = false;
        state.isAuthenticated = false;
        state.token = null;
        state.user = null;
      });
  },
});

export const { logout, setUser } = authSlice.actions;
export default authSlice.reducer;
