import { useState } from 'react';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { updateFeedback } from '../store/feedbackSlice';
import api from '../services/api';
import type { Feedback } from '../types';

const FeedbackList = () => {
  const dispatch = useAppDispatch();
  const { items: feedbacks } = useAppSelector((state) => state.feedback);
  const { user } = useAppSelector((state) => state.auth);
  const [sentimentFilter, setSentimentFilter] = useState<string>('all');
  const [generatingResponse, setGeneratingResponse] = useState<number | null>(null);

  const filteredFeedbacks = feedbacks.filter((feedback) => {
    if (sentimentFilter !== 'all' && feedback.sentiment !== sentimentFilter) return false;
    return true;
  });

  const handleGenerateResponse = async (feedback: Feedback) => {
    setGeneratingResponse(feedback.id);
    try {
      const response = await api.post(`/api/feedback/${feedback.id}/generate-response`);
      const updatedFeedback = {
        ...feedback,
        smart_response: response.data.smart_response,
      };
      dispatch(updateFeedback(updatedFeedback));
    } catch (error) {
      console.error('Error generating response:', error);
    } finally {
      setGeneratingResponse(null);
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'Positive':
        return 'bg-green-100 text-green-800';
      case 'Negative':
        return 'bg-red-100 text-red-800';
      case 'Neutral':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Guest Feedback</h2>
        <div className="mt-4">
          <select
            value={sentimentFilter}
            onChange={(e) => setSentimentFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Sentiment</option>
            <option value="Positive">Positive</option>
            <option value="Negative">Negative</option>
            <option value="Neutral">Neutral</option>
          </select>
        </div>
      </div>

      <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
        {filteredFeedbacks.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            No feedback found
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredFeedbacks.map((feedback) => (
              <div key={feedback.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="mb-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSentimentColor(feedback.sentiment)}`}>
                    {feedback.sentiment}
                  </span>
                </div>
                <p className="text-sm text-gray-900 mb-2">{feedback.message}</p>
                <div className="text-xs text-gray-500 mb-3">
                  Room {feedback.room?.room_number} • {new Date(feedback.created_at).toLocaleString()}
                </div>

                {feedback.smart_response && (
                  <div className="mt-3 p-3 bg-indigo-50 border border-indigo-200 rounded-md">
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-xs font-medium text-indigo-900">Smart Response</span>
                    </div>
                    <p className="text-sm text-indigo-900">{feedback.smart_response}</p>
                  </div>
                )}

                {user?.role === 'Manager' && feedback.sentiment === 'Negative' && !feedback.smart_response && (
                  <button
                    onClick={() => handleGenerateResponse(feedback)}
                    disabled={generatingResponse === feedback.id}
                    className="mt-3 px-3 py-1 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generatingResponse === feedback.id ? 'Generating...' : 'Generate Smart Response'}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default FeedbackList;
