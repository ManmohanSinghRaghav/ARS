/**
 * Axios API client with JWT interceptor.
 */
import axios from 'axios';
import { auth } from '../firebase';

const API_BASE = '/api';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 1000 * 60 * 45, // 45 minutes (pipeline can be long)
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor: attach JWT ──
client.interceptors.request.use(async (config) => {
  const user = auth.currentUser;
  if (user) {
    const token = await user.getIdToken(true);
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
  // Sync user info with backend if necessary
  me: () => client.get('/auth/me'),
};

export const runsAPI = {
  create: (topic: string, vibe: string = 'Deep Academic', commands: string = '') => client.post('/runs', { topic, vibe, commands }),
  list: (skip = 0, limit = 20) => client.get(`/runs?skip=${skip}&limit=${limit}`),
  get: (id: string) => client.get(`/runs/${id}`),
  progress: (id: string) => client.get(`/runs/${id}/progress`),
  downloadPaper: (id: string) => client.get(`/runs/${id}/paper`, { responseType: 'text' }),
  downloadPaperPdf: (id: string) => client.get(`/runs/${id}/paper.pdf`, { responseType: 'blob' }),
  delete: (id: string) => client.delete(`/runs/${id}`),
  updatePaper: (id: string, markdown: string) => client.patch(`/runs/${id}/paper`, { paper_markdown: markdown }),
  refinePaper: (id: string, feedback: string) => client.post(`/runs/${id}/refine`, { feedback }),
};

export const settingsAPI = {
  get: () => client.get('/settings'),
  update: (data: Record<string, string | undefined>) => client.put('/settings', data),
};

export default client;
