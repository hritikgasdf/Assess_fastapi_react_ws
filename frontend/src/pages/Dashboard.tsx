import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { logout } from '../store/authSlice';
import { setRequests } from '../store/requestsSlice';
import { setFeedback } from '../store/feedbackSlice';
import { useWebSocket } from '../hooks/useWebSocket';
import api from '../services/api';
import RequestsList from '../components/RequestsList';
import FeedbackList from '../components/FeedbackList';
import { ErrorModal } from '../components/ErrorModal';

const Dashboard = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { user, token } = useAppSelector((state) => state.auth);
  const [loading, setLoading] = useState(true);

  const { connectionError, clearError } = useWebSocket(token);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [requestsRes, feedbackRes] = await Promise.all([
          api.get('/api/requests'),
          api.get('/api/feedback'),
        ]);
        dispatch(setRequests(requestsRes.data));
        dispatch(setFeedback(feedbackRes.data));
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [dispatch]);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Hotel Operations Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm">
                <span className="text-gray-600">Welcome, </span>
                <span className="font-medium text-gray-900">{user?.full_name}</span>
                <span className={`ml-2 px-2 py-1 rounded-full text-xs ${
                  user?.role === 'Manager' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                }`}>
                  {user?.role}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RequestsList />
          <FeedbackList />
        </div>
      </main>

      {/* WebSocket Connection Error Modal */}
      <ErrorModal
        isOpen={!!connectionError}
        title="Real-time Connection Failed"
        message={connectionError || ''}
        onClose={clearError}
      />
    </div>
  );
};

export default Dashboard;
