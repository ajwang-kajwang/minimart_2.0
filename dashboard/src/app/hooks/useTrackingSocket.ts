import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

// Types matching Flask backend output
export interface TrackedPerson {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  active: boolean;
  age: number;
  color: [number, number, number];
  center_pixel?: [number, number];
  real_world?: {
    x: number;
    y: number;
  };
}

export interface TrackingUpdate {
  active_count: number;
  fps: number;
  people: TrackedPerson[];
  timestamp?: number;
}

export interface ConnectionState {
  connected: boolean;
  error: string | null;
  reconnectAttempts: number;
}

interface UseTrackingSocketOptions {
  url?: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export function useTrackingSocket(options: UseTrackingSocketOptions = {}) {
  const {
    url = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000',
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectDelay = 2000,
  } = options;

  const socketRef = useRef<Socket | null>(null);
  // Add a state to trigger re-renders when socket is ready
  const [socketInstance, setSocketInstance] = useState<Socket | null>(null);

  const [connectionState, setConnectionState] = useState<ConnectionState>({
    connected: false,
    error: null,
    reconnectAttempts: 0,
  });

  const [trackingData, setTrackingData] = useState<TrackingUpdate>({
    active_count: 0,
    fps: 0,
    people: [],
  });

  // Track historical data for analytics
  const [fpsHistory, setFpsHistory] = useState<number[]>([]);
  const [countHistory, setCountHistory] = useState<number[]>([]);

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;

    const socket = io(url, {
      transports: ['websocket', 'polling'],
      timeout: 10000,
      reconnection: true,
      reconnectionAttempts: reconnectAttempts,
      reconnectionDelay: reconnectDelay,
    });

    socket.on('connect', () => {
      console.log('✅ Connected to tracking backend');
      setConnectionState({
        connected: true,
        error: null,
        reconnectAttempts: 0,
      });
    });

    socket.on('disconnect', (reason) => {
      console.log('❌ Disconnected from backend:', reason);
      setConnectionState((prev) => ({
        ...prev,
        connected: false,
        error: `Disconnected: ${reason}`,
      }));
    });

    socket.on('connect_error', (error) => {
      console.error('Connection error:', error.message);
      setConnectionState((prev) => ({
        ...prev,
        connected: false,
        error: error.message,
        reconnectAttempts: prev.reconnectAttempts + 1,
      }));
    });

    // Main tracking data event from Flask backend
    socket.on('coordinate_tracking_update', (data: TrackingUpdate) => {
      const enrichedData = {
        ...data,
        timestamp: Date.now(),
      };
      
      setTrackingData(enrichedData);
      
      // Update history (keep last 60 samples for charts)
      setFpsHistory((prev) => [...prev.slice(-59), data.fps]);
      setCountHistory((prev) => [...prev.slice(-59), data.active_count]);
    });

    socketRef.current = socket;
    setSocketInstance(socket);
  }, [url, reconnectAttempts, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setSocketInstance(null); // Ensure state is cleared
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    // Connection
    connect,
    disconnect,
    connectionState,
    
    // EXPOSED SOCKET OBJECT (Essential for Chatbot)
    socket: socketInstance, 
    
    // Data
    trackingData,
    fpsHistory,
    countHistory,
    
    // Computed
    isConnected: connectionState.connected,
    activePeople: trackingData.people.filter((p) => p.active),
  };
}

export default useTrackingSocket;