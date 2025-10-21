import { useEffect, useRef, useState, useCallback } from 'react';
import { useAppDispatch } from '../store/hooks';
import { addRequest, updateRequest } from '../store/requestsSlice';
import { addFeedback, updateFeedback } from '../store/feedbackSlice';
import type { Request, Feedback } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 3000; // 3 seconds

export const useWebSocket = (token: string | null) => {
  const dispatch = useAppDispatch();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(null);
  const retryCountRef = useRef<number>(0);
  const hasShownErrorRef = useRef<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Store dispatch in a ref to avoid reconnections on dispatch changes
  const dispatchRef = useRef(dispatch);
  useEffect(() => {
    dispatchRef.current = dispatch;
  }, [dispatch]);

  useEffect(() => {
    if (!token) return;

    // Prevent multiple simultaneous connection attempts
    let isConnecting = false;
    let isCleaning = false;

    const showConnectionError = () => {
      if (!hasShownErrorRef.current) {
        hasShownErrorRef.current = true;
        setConnectionError(
          'Unable to establish real-time connection. Please check your internet connection and refresh the page.'
        );
      }
    };

    const connect = () => {
      if (isConnecting) {
        console.log('Connection already in progress, skipping...');
        return;
      }
      isConnecting = true;
      // Check if we've exceeded max retry attempts
      if (retryCountRef.current >= MAX_RETRY_ATTEMPTS) {
        console.error('Max WebSocket retry attempts reached. Giving up.');
        showConnectionError();
        return;
      }

      try {
        const ws = new WebSocket(`${WS_URL}/ws?token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected successfully');
          isConnecting = false;
          // Reset retry count on successful connection
          retryCountRef.current = 0;
          hasShownErrorRef.current = false;
          setConnectionError(null);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            
            // Use dispatchRef.current to avoid stale closures
            switch (message.type) {
              case 'new_request':
                dispatchRef.current(addRequest(message.data as Request));
                break;
              case 'request_updated':
                dispatchRef.current(updateRequest(message.data as Request));
                break;
              case 'new_feedback':
                dispatchRef.current(addFeedback(message.data as Feedback));
                break;
              case 'feedback_updated':
                dispatchRef.current(updateFeedback(message.data as Feedback));
                break;
            }
          } catch (error) {
            console.error('WebSocket message error:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          isConnecting = false;
          retryCountRef.current++;
        };

        ws.onclose = (event) => {
          const code = event?.code || 'unknown';
          console.log(`WebSocket disconnected (Code: ${code}). Attempt ${retryCountRef.current + 1}/${MAX_RETRY_ATTEMPTS}`);
          isConnecting = false;
          
          // Don't reconnect if cleaning up
          if (isCleaning) {
            console.log('Cleanup in progress, not reconnecting');
            return;
          }
          
          // Increment retry count
          retryCountRef.current++;

          // Only attempt to reconnect if we haven't exceeded max attempts
          if (retryCountRef.current < MAX_RETRY_ATTEMPTS) {
            console.log(`Reconnecting in ${RETRY_DELAY / 1000} seconds...`);
            reconnectTimeoutRef.current = window.setTimeout(connect, RETRY_DELAY);
          } else {
            console.error('Max retry attempts reached. Not reconnecting.');
            showConnectionError();
          }
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        isConnecting = false;
        retryCountRef.current++;
        
        if (retryCountRef.current < MAX_RETRY_ATTEMPTS && !isCleaning) {
          reconnectTimeoutRef.current = window.setTimeout(connect, RETRY_DELAY);
        } else {
          showConnectionError();
        }
      }
    };

    connect();

    return () => {
      isCleaning = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        console.log('Closing WebSocket on cleanup');
        wsRef.current.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]); // Only depend on token, use dispatchRef for dispatch

  return { ws: wsRef.current, connectionError, clearError: () => setConnectionError(null) };
};
