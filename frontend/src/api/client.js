import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 – clear tokens and redirect to /auth
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = '/auth';
    }
    return Promise.reject(err);
  }
);

// ─── Auth ──────────────────────────────────────────────────────────────────────
export const authAPI = {
  /** POST /api/auth/signin  – Register a new user */
  signin: (data) =>
    api.post('/api/auth/signin', data).then((r) => r.data),

  /** POST /api/auth/login  – Login and get tokens */
  login: (data) =>
    api.post('/api/auth/login', data).then((r) => r.data),

  /** POST /api/auth/logout – end session */
  logout: (sessionId) =>
    api.post(`/api/auth/logout?id=${sessionId}`).then((r) => r.data),

  /** POST /api/tokens/renew – refresh access token */
  renewToken: (refreshToken) =>
    api.post('/api/tokens/renew', { refresh_token: refreshToken }).then((r) => r.data),

  /** GET /api/me – current user profile */
  getMe: () =>
    api.get('/api/me').then((r) => r.data),

  /** PUT /api/user_details – update user health profile */
  updateUserDetails: (data) =>
    api.put('/api/user_details', data).then((r) => r.data),
};

// ─── Reports ───────────────────────────────────────────────────────────────────
export const reportsAPI = {
  /**
   * POST /api/reports/add
   * multipart/form-data: patient_id, patient_name, file
   */
  addReport: (formData) =>
    api.post('/api/reports/add', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: formData._onProgress || undefined,
    }).then((r) => r.data),

  /** GET /api/reports/ – list all reports (supports status, skip, limit) */
  getAll: (params = {}) =>
    api.get('/api/reports/', { params }).then((r) => r.data),

  /** GET /api/reports/{id} – single report detail */
  getById: (id) =>
    api.get(`/api/reports/${id}`).then((r) => r.data),

  /** PUT /api/reports/update/{id} */
  update: (id, data) =>
    api.put(`/api/reports/update/${id}`, data).then((r) => r.data),

  /** DELETE /api/reports/delete/{id} */
  delete: (id) =>
    api.delete(`/api/reports/delete/${id}`).then((r) => r.data),
};

// ─── Medications ───────────────────────────────────────────────────────────────
export const medicationsAPI = {
  /** GET /api/medications/ */
  getAll: (params = {}) =>
    api.get('/api/medications/', { params }).then((r) => r.data),

  /** POST /api/medications/ */
  add: (data) =>
    api.post('/api/medications/', data).then((r) => r.data),

  /** PUT /api/medications/{id} */
  update: (id, data) =>
    api.put(`/api/medications/${id}`, data).then((r) => r.data),

  /** DELETE /api/medications/{id} */
  delete: (id) =>
    api.delete(`/api/medications/${id}`).then((r) => r.data),
};

export default api;
