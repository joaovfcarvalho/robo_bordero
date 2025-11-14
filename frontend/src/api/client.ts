import axios from 'axios'
import type {
  AnalyticsResponse,
  MatchDetail,
  MatchDetailResponse,
  PDFInfo,
  QueueStatusResponse,
  ScrapeRequest,
  ScrapeResponse,
  LoginRequest,
  LoginResponse,
  BulkScrapeRequest,
  BulkScrapeResponse,
  AdminStats,
} from '../types'

// Base API client
// For Vercel deployment, use VITE_API_URL environment variable to point to Railway backend
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

// Analytics API
export const analyticsApi = {
  getOverview: (params?: {
    start_date?: string
    end_date?: string
    competition?: string
    team?: string
  }) => api.get<AnalyticsResponse>('/analytics/overview', { params }).then(res => res.data),

  getMatches: (params?: {
    start_date?: string
    end_date?: string
    competition?: string
    team?: string
    stadium?: string
    year?: number
    limit?: number
  }) => api.get<MatchDetail[]>('/analytics/matches', { params }).then(res => res.data),

  getMatchDetail: (id: string) =>
    api.get<MatchDetailResponse>(`/analytics/matches/${id}`).then(res => res.data),

  getCompetitions: () =>
    api.get<string[]>('/analytics/filters/competitions').then(res => res.data),

  getTeams: () =>
    api.get<string[]>('/analytics/filters/teams').then(res => res.data),

  getStadiums: () =>
    api.get<string[]>('/analytics/filters/stadiums').then(res => res.data),
}

// PDFs API
export const pdfsApi = {
  getAvailable: (params?: {
    year?: number
    competition?: string
    processed_only?: boolean
    unprocessed_only?: boolean
  }) => api.get<PDFInfo[]>('/pdfs/available', { params }).then(res => res.data),

  getQueueStatus: () =>
    api.get<QueueStatusResponse>('/pdfs/queue').then(res => res.data),

  scrapePDF: (data: ScrapeRequest) =>
    api.post<ScrapeResponse>('/pdfs/scrape', data).then(res => res.data),

  removeFromQueue: (id: string) =>
    api.delete(`/pdfs/queue/${id}`).then(res => res.data),

  retryFailed: (id: string) =>
    api.post(`/pdfs/queue/retry/${id}`).then(res => res.data),
}

// Admin API
export const adminApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/admin/login', data).then(res => res.data),

  logout: () =>
    api.post('/admin/logout').then(res => res.data),

  bulkScrape: (data: BulkScrapeRequest) =>
    api.post<BulkScrapeResponse>('/admin/bulk-scrape', data).then(res => res.data),

  getStats: () =>
    api.get<AdminStats>('/admin/stats').then(res => res.data),

  refreshNormalizations: () =>
    api.post('/admin/refresh-normalizations').then(res => res.data),

  deleteMatch: (id: string) =>
    api.delete(`/admin/matches/${id}`).then(res => res.data),
}

// Helper functions
export const isAuthenticated = () => {
  return !!localStorage.getItem('auth_token')
}

export const setAuthToken = (token: string) => {
  localStorage.setItem('auth_token', token)
}

export const clearAuthToken = () => {
  localStorage.removeItem('auth_token')
}
