/**
 * Axios client configured for the FastAPI backend.
 * Automatically attaches Bearer token from localStorage.
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request Interceptor — attach JWT ──────────────────────────
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor — normalize errors ───────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear stale token and redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ── Auth API ──────────────────────────────────────────────────

export const authApi = {
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    apiClient.post('/api/auth/register', data),

  login: (data: { email: string; password: string }) =>
    apiClient.post('/api/auth/login', data),

  me: () =>
    apiClient.get('/api/auth/me'),

  updateMe: (data: { full_name?: string | null }) =>
    apiClient.patch('/api/auth/me', data),

  changePassword: (data: {
    current_password: string;
    new_password: string;
    confirm_new_password: string;
  }) => apiClient.post('/api/auth/change-password', data),
};

// ── Health API ────────────────────────────────────────────────

export const healthApi = {
  check: () => apiClient.get('/api/health'),
};

// ── Targets API ───────────────────────────────────────────────

export const targetsApi = {
  list: () => apiClient.get('/api/targets'),
  get: (id: number) => apiClient.get(`/api/targets/${id}`),
  create: (data: {
    name: string;
    chembl_id?: string;
    uniprot_id?: string;
    organism?: string;
    target_type?: string;
    description?: string;
    pdb_id?: string;
  }) => apiClient.post('/api/targets', data),
};

// ── Experiments API ───────────────────────────────────────────

export const experimentsApi = {
  create: (data: {
    name: string;
    description?: string;
    target_id?: number;
    dataset_path?: string;
    dataset_version?: string;
  }) => apiClient.post('/api/experiments', data),

  list: () => apiClient.get('/api/experiments'),

  get: (id: number) => apiClient.get(`/api/experiments/${id}`),

  update: (id: number, data: {
    name?: string;
    description?: string;
    status?: string;
  }) => apiClient.patch(`/api/experiments/${id}`, data),

  delete: (id: number) => apiClient.delete(`/api/experiments/${id}`),

  stats: () => apiClient.get('/api/experiments/stats'),
};

// ── Pipeline & ML API ─────────────────────────────────────────

export const pipelineApi = {
  preprocess: (expId: number) =>
    apiClient.post(`/api/experiments/${expId}/preprocess`),

  getPreprocessReport: (expId: number) =>
    apiClient.get(`/api/experiments/${expId}/preprocess-report`),

  getModelMetrics: (expId: number) =>
    apiClient.get(`/api/experiments/${expId}/model-metrics`),

  predict: (expId: number, modelName: string = 'RandomForest') =>
    apiClient.post(`/api/experiments/${expId}/predict`, null, {
      params: { model_name: modelName },
    }),

  getPredictions: (
    expId: number,
    params: {
      model_name?: string;
      limit?: number;
      offset?: number;
      min_pIC50?: number;
      search?: string;
    } = {}
  ) =>
    apiClient.get(`/api/experiments/${expId}/predictions`, { params }),
};

// ── ADMET API ────────────────────────────────────────────────

export const admetApi = {
  runScreening: (expId: number, topN: number = 100) =>
    apiClient.post(`/api/experiments/${expId}/admet`, null, { params: { top_n_input: topN } }),

  getResults: (expId: number, params: Record<string, unknown> = {}) =>
    apiClient.get(`/api/experiments/${expId}/admet`, { params }),

  getModelInfo: (expId: number) =>
    apiClient.get(`/api/experiments/${expId}/admet/models`),
};

// ── Quantum API ──────────────────────────────────────────────

export const quantumApi = {
  run: (expId: number, body: Record<string, unknown>) =>
    apiClient.post(`/api/experiments/${expId}/quantum`, body),

  get: (expId: number) =>
    apiClient.get(`/api/experiments/${expId}/quantum`),

  getCandidates: (expId: number, params: Record<string, unknown> = {}) =>
    apiClient.get(`/api/experiments/${expId}/quantum/candidates`, { params }),
};

// ── Docking API ──────────────────────────────────────────────
export const dockingApi = {
  run: (expId: number, body: {
    pdb_id?: string;
    exhaustiveness?: number;
    n_candidates?: number;
    grid_box?: { center: number[]; size: number[] } | null;
  }) =>
    apiClient.post(`/api/experiments/${expId}/docking`, body),

  get: (expId: number) =>
    apiClient.get(`/api/experiments/${expId}/docking`),
};

// ── Ranking API ──────────────────────────────────────────────
export const rankingApi = {
  compute: (expId: number, body: {
    weights?: Record<string, number>;
    include_docking?: boolean;
  } = {}) =>
    apiClient.post(`/api/experiments/${expId}/ranking`, body),

  get: (expId: number, params: { limit?: number; offset?: number } = {}) =>
    apiClient.get(`/api/experiments/${expId}/ranking`, { params }),

  downloadCsv: (expId: number) =>
    apiClient.get(`/api/experiments/${expId}/ranking/csv`, { responseType: 'blob' }),
};

export default apiClient;
