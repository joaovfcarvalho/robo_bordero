// Type definitions matching the FastAPI backend models

export interface GeneralStats {
  total_matches: number
  total_attendance: number
  total_revenue: number
  average_ticket_price: number
  average_net_margin: number
}

export interface CompetitionSummary {
  competicao: string
  total_games: number
  total_revenue: number
  total_attendance: number
  average_net_margin: number
}

export interface TeamStats {
  team_name: string
  average_attendance: number
  average_ticket_price: number
  average_net_margin: number
  total_matches: number
}

export interface StadiumStats {
  stadium_name: string
  average_attendance: number
  average_ticket_price: number
  total_matches: number
}

export interface TopMatch {
  id_jogo_cbf: string
  data_jogo: string
  time_mandante: string
  time_visitante: string
  estadio: string
  value: number
  metric: string
}

export interface AnalyticsResponse {
  general_stats: GeneralStats
  competition_summary: CompetitionSummary[]
  top_teams_by_attendance: TeamStats[]
  top_stadiums: StadiumStats[]
  top_matches: TopMatch[]
}

export interface MatchDetail {
  id_jogo_cbf: string
  data_jogo: string
  hora_inicio?: string
  competicao: string
  time_mandante: string
  time_visitante: string
  estadio: string
  cidade?: string
  uf?: string
  placar_mandante?: number
  placar_visitante?: number
  publico_total: number
  publico_pagante: number
  publico_nao_pagante: number
  receita_total: number
  despesa_total: number
  saldo: number
  preco_ingresso_medio?: number
  processado_em?: string
}

export interface RevenueDetail {
  categoria: string
  subcategoria?: string
  valor: number
}

export interface ExpenseDetail {
  categoria: string
  subcategoria?: string
  valor: number
}

export interface MatchDetailResponse {
  match: MatchDetail
  revenues: RevenueDetail[]
  expenses: ExpenseDetail[]
}

export interface PDFInfo {
  id_jogo_cbf: string
  competicao: string
  ano: number
  time_mandante?: string
  time_visitante?: string
  data_jogo?: string
  pdf_url: string
  processed: boolean
  processado_em?: string
}

export interface QueueItem {
  id_jogo_cbf: string
  pdf_url: string
  competicao: string
  ano: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  tentativas: number
  ultimo_erro?: string
  adicionado_em: string
  processado_em?: string
}

export interface QueueStatusResponse {
  total_pending: number
  total_processing: number
  total_completed: number
  total_failed: number
  recent_items: QueueItem[]
}

export interface ScrapeRequest {
  id_jogo_cbf: string
  pdf_url: string
  competicao: string
  ano: number
  force_reprocess?: boolean
}

export interface ScrapeResponse {
  success: boolean
  message: string
  id_jogo_cbf: string
  job_id?: string
}

export interface LoginRequest {
  password: string
}

export interface LoginResponse {
  success: boolean
  token?: string
  message: string
}

export interface BulkScrapeRequest {
  year: number
  competition_codes?: string[]
  force_reprocess?: boolean
}

export interface BulkScrapeResponse {
  success: boolean
  message: string
  job_id: string
  estimated_pdfs: number
}

export interface AdminStats {
  total_matches: number
  total_queue_items: number
  queue_pending: number
  queue_processing: number
  queue_failed: number
  pdfs_stored: number
}
