"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


class QueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Analytics Models
class GeneralStats(BaseModel):
    total_matches: int
    total_attendance: int
    total_revenue: float
    average_ticket_price: float
    average_net_margin: float


class CompetitionSummary(BaseModel):
    competicao: str
    total_games: int
    total_revenue: float
    total_attendance: int
    average_net_margin: float


class TeamStats(BaseModel):
    team_name: str
    average_attendance: int
    average_ticket_price: float
    average_net_margin: float
    total_matches: int


class StadiumStats(BaseModel):
    stadium_name: str
    average_attendance: int
    average_ticket_price: float
    total_matches: int


class TopMatch(BaseModel):
    id_jogo_cbf: str
    data_jogo: date
    time_mandante: str
    time_visitante: str
    estadio: str
    value: float
    metric: str


class AnalyticsResponse(BaseModel):
    general_stats: GeneralStats
    competition_summary: List[CompetitionSummary]
    top_teams_by_attendance: List[TeamStats]
    top_stadiums: List[StadiumStats]
    top_matches: List[TopMatch]


# PDF Management Models
class PDFInfo(BaseModel):
    id_jogo_cbf: str
    competicao: str
    ano: int
    time_mandante: Optional[str] = None
    time_visitante: Optional[str] = None
    data_jogo: Optional[date] = None
    pdf_url: str
    processed: bool
    processado_em: Optional[datetime] = None


class ScrapeRequest(BaseModel):
    id_jogo_cbf: str
    pdf_url: str
    competicao: str
    ano: int
    force_reprocess: bool = False


class ScrapeResponse(BaseModel):
    success: bool
    message: str
    id_jogo_cbf: str
    job_id: Optional[str] = None


class QueueItem(BaseModel):
    id_jogo_cbf: str
    pdf_url: str
    competicao: str
    ano: int
    status: QueueStatus
    tentativas: int
    ultimo_erro: Optional[str] = None
    adicionado_em: datetime
    processado_em: Optional[datetime] = None


class QueueStatusResponse(BaseModel):
    total_pending: int
    total_processing: int
    total_completed: int
    total_failed: int
    recent_items: List[QueueItem]


# Match Data Models
class MatchFilters(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    competition: Optional[str] = None
    team: Optional[str] = None
    stadium: Optional[str] = None
    year: Optional[int] = None
    limit: Optional[int] = Field(default=100, le=1000)


class MatchDetail(BaseModel):
    id_jogo_cbf: str
    data_jogo: date
    hora_inicio: Optional[str] = None
    competicao: str
    time_mandante: str
    time_visitante: str
    estadio: str
    cidade: Optional[str] = None
    uf: Optional[str] = None
    placar_mandante: Optional[int] = None
    placar_visitante: Optional[int] = None
    publico_total: int
    publico_pagante: int
    publico_nao_pagante: int
    receita_total: float
    despesa_total: float
    saldo: float
    preco_ingresso_medio: Optional[float] = None
    processado_em: Optional[datetime] = None


class RevenueDetail(BaseModel):
    categoria: str
    subcategoria: Optional[str] = None
    valor: float


class ExpenseDetail(BaseModel):
    categoria: str
    subcategoria: Optional[str] = None
    valor: float


class MatchDetailResponse(BaseModel):
    match: MatchDetail
    revenues: List[RevenueDetail]
    expenses: List[ExpenseDetail]


# Admin Models
class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


class BulkScrapeRequest(BaseModel):
    year: int
    competition_codes: Optional[List[str]] = None  # If None, use all default competitions
    force_reprocess: bool = False


class BulkScrapeResponse(BaseModel):
    success: bool
    message: str
    job_id: str
    estimated_pdfs: int
