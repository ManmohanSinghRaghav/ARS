/**
 * Axios API client with JWT interceptor.
 */
import axios from 'axios';

const API_BASE = '/api';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 1000 * 60 * 45, // 45 minutes (pipeline can be long)
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor: attach JWT ──
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle 401 ──
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ── API methods ──
export const authAPI = {
  register: (data: { username: string; email: string; password: string }) =>
    client.post('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    client.post('/auth/login', data),
  me: () => client.get('/auth/me'),
};

export const runsAPI = {
  create: (topic: string) => client.post('/runs', { topic }),
  list: (skip = 0, limit = 20) => client.get(`/runs?skip=${skip}&limit=${limit}`),
  get: (id: number) => client.get(`/runs/${id}`),
  progress: (id: number) => client.get(`/runs/${id}/progress`),
  downloadPaper: (id: number) => client.get(`/runs/${id}/paper`, { responseType: 'text' }),
  delete: (id: number) => client.delete(`/runs/${id}`),
};

export const settingsAPI = {
  get: () => client.get('/settings'),
  update: (data: Record<string, string | undefined>) => client.put('/settings', data),
};

export default client;
