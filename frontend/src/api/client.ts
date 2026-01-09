import axios from 'axios';
import type {
  Case,
  Email,
  Attachment,
  CaseFilters,
  BatchProcessResult,
  QueueStatus,
  QueueHealth,
  RetryResult,
  RetryAllResult
} from '../types';

// Use environment variable for API base URL (falls back to /api for development)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const casesApi = {
  getAll: async (filters?: CaseFilters) => {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.exam_type) params.append('exam_type', filters.exam_type);
    if (filters?.min_confidence !== undefined) {
      params.append('min_confidence', filters.min_confidence.toString());
    }

    const { data } = await apiClient.get<Case[]>(`/cases/?${params.toString()}`);
    return data;
  },

  getById: async (id: string) => {
    const { data } = await apiClient.get<Case>(`/cases/${id}`);
    return data;
  },

  update: async (id: string, updates: Partial<Case>) => {
    const { data } = await apiClient.patch<Case>(`/cases/${id}`, updates);
    return data;
  },

  delete: async (id: string) => {
    const { data } = await apiClient.delete<{ message: string; case_id: string; case_number: string }>(`/cases/${id}`);
    return data;
  },
};

export const emailsApi = {
  processBatch: async () => {
    const { data } = await apiClient.post<BatchProcessResult>('/emails/simulate-batch');
    return data;
  },

  getById: async (id: string) => {
    const { data } = await apiClient.get<Email>(`/emails/${id}`);
    return data;
  },

  getAll: async (status?: string) => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    const { data } = await apiClient.get<Email[]>(`/emails/?${params.toString()}`);
    return data;
  },

  retry: async (emailId: string) => {
    const { data } = await apiClient.post<RetryResult>(`/emails/${emailId}/retry`);
    return data;
  },

  retryAll: async () => {
    const { data } = await apiClient.post<RetryAllResult>('/emails/retry-all-failed');
    return data;
  },
};

export const attachmentsApi = {
  getAll: async (category?: string, caseId?: string) => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (caseId) params.append('case_id', caseId);

    const { data } = await apiClient.get<Attachment[]>(`/attachments/?${params.toString()}`);
    return data;
  },

  getByCase: async (caseId: string) => {
    const { data } = await apiClient.get<Attachment[]>(`/attachments/case/${caseId}/attachments`);
    return data;
  },
};

export const queueApi = {
  getStatus: async () => {
    const { data } = await apiClient.get<QueueStatus>('/queue/status');
    return data;
  },

  getHealth: async () => {
    const { data } = await apiClient.get<QueueHealth>('/queue/health');
    return data;
  },

  cleanup: async () => {
    const { data } = await apiClient.post('/queue/cleanup');
    return data;
  },
};
