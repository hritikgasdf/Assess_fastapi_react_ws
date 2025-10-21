import { useState } from 'react';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { updateRequest } from '../store/requestsSlice';
import api from '../services/api';
import type { Request } from '../types';

const RequestsList = () => {
  const dispatch = useAppDispatch();
  const { items: requests } = useAppSelector((state) => state.requests);
  const { user } = useAppSelector((state) => state.auth);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const filteredRequests = requests.filter((request) => {
    if (statusFilter !== 'all' && request.status !== statusFilter) return false;
    if (categoryFilter !== 'all' && request.category !== categoryFilter) return false;
    return true;
  });

  const categories = Array.from(new Set(requests.map((r) => r.category)));

  const handleMarkComplete = async (request: Request) => {
    try {
      const response = await api.patch(`/api/requests/${request.id}`, {
        status: 'Completed',
      });
      dispatch(updateRequest(response.data));
    } catch (error) {
      console.error('Error updating request:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'In Progress':
        return 'bg-blue-100 text-blue-800';
      case 'Completed':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Guest Requests</h2>
        <div className="mt-4 flex flex-col sm:flex-row gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Status</option>
            <option value="Pending">Pending</option>
            <option value="In Progress">In Progress</option>
            <option value="Completed">Completed</option>
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
        {filteredRequests.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            No requests found
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredRequests.map((request) => (
              <div key={request.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                        {request.status}
                      </span>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {request.category}
                      </span>
                    </div>
                    <p className="text-sm text-gray-900 mb-2">{request.description}</p>
                    <div className="text-xs text-gray-500">
                      Room {request.room?.room_number} • {new Date(request.created_at).toLocaleString()}
                    </div>
                  </div>
                  {user?.role === 'Manager' && request.status !== 'Completed' && (
                    <button
                      onClick={() => handleMarkComplete(request)}
                      className="ml-4 px-3 py-1 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
                    >
                      Mark Complete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RequestsList;
