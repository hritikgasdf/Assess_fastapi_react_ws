export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'Staff' | 'Manager';
  created_at: string;
}

export interface Guest {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  created_at: string;
}

export interface Room {
  id: number;
  room_number: string;
  room_type: string;
  floor: number;
  created_at: string;
}

export interface Request {
  id: number;
  guest_id: number;
  room_id: number;
  category: string;
  description: string;
  status: 'Pending' | 'In Progress' | 'Completed';
  created_at: string;
  updated_at: string;
  guest?: Guest;
  room?: Room;
}

export interface Feedback {
  id: number;
  guest_id: number;
  room_id: number;
  message: string;
  sentiment: 'Positive' | 'Negative' | 'Neutral';
  smart_response?: string;
  created_at: string;
  guest?: Guest;
  room?: Room;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  full_name: string;
  password: string;
  role?: 'Staff' | 'Manager';
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}
