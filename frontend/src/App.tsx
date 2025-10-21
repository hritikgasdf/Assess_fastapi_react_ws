import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { useEffect } from 'react';
import { store } from './store';
import { useAppDispatch } from './store/hooks';
import { checkAuth } from './store/authSlice';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ProtectedRoute from './components/ProtectedRoute';

function AuthChecker() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(checkAuth());
  }, [dispatch]);

  return null;
}

function App() {
  return (
    <Provider store={store}>
      <BrowserRouter>
        <AuthChecker />
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </Provider>
  );
}

export default App;
