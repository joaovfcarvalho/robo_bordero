"""
Analytics API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import date
import pandas as pd
from collections import defaultdict

from src.database import SupabaseDatabase
from src.api.models import (
    AnalyticsResponse,
    GeneralStats,
    CompetitionSummary,
    TeamStats,
    StadiumStats,
    TopMatch,
    MatchFilters,
    MatchDetail,
    MatchDetailResponse,
    RevenueDetail,
    ExpenseDetail,
)

router = APIRouter()


def calculate_ticket_medio(row):
    """Calculate average ticket price"""
    if row.get('publico_total') and row['publico_total'] > 0:
        receita = row.get('receita_total', 0)
        return receita / row['publico_total']
    return 0.0


def calculate_margem_liquida(row):
    """Calculate net margin percentage"""
    if row.get('receita_total') and row['receita_total'] > 0:
        saldo = row.get('saldo', 0)
        return (saldo / row['receita_total']) * 100
    return 0.0


@router.get("/overview", response_model=AnalyticsResponse)
async def get_analytics_overview(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    competition: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
):
    """Get comprehensive analytics overview"""
    try:
        db = SupabaseDatabase()

        # Build query
        query = db.client.table("jogos_resumo").select("*")

        if start_date:
            query = query.gte("data_jogo", start_date.isoformat())
        if end_date:
            query = query.lte("data_jogo", end_date.isoformat())
        if competition:
            query = query.eq("competicao", competition)
        if team:
            # Team can be home or away
            query = query.or_(f"time_mandante.eq.{team},time_visitante.eq.{team}")

        # Execute query
        response = query.execute()
        matches = response.data

        if not matches:
            # Return empty stats
            return AnalyticsResponse(
                general_stats=GeneralStats(
                    total_matches=0,
                    total_attendance=0,
                    total_revenue=0.0,
                    average_ticket_price=0.0,
                    average_net_margin=0.0,
                ),
                competition_summary=[],
                top_teams_by_attendance=[],
                top_stadiums=[],
                top_matches=[],
            )

        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(matches)

        # Calculate derived metrics
        df['ticket_medio'] = df.apply(calculate_ticket_medio, axis=1)
        df['margem_liquida'] = df.apply(calculate_margem_liquida, axis=1)

        # General Statistics
        general_stats = GeneralStats(
            total_matches=len(df),
            total_attendance=int(df['publico_total'].sum()),
            total_revenue=float(df['receita_total'].sum()),
            average_ticket_price=float(df['ticket_medio'].mean()),
            average_net_margin=float(df['margem_liquida'].mean()),
        )

        # Competition Summary
        comp_groups = df.groupby('competicao').agg({
            'id_jogo_cbf': 'count',
            'receita_total': 'sum',
            'publico_total': 'sum',
            'margem_liquida': 'mean',
        }).reset_index()

        competition_summary = [
            CompetitionSummary(
                competicao=row['competicao'],
                total_games=int(row['id_jogo_cbf']),
                total_revenue=float(row['receita_total']),
                total_attendance=int(row['publico_total']),
                average_net_margin=float(row['margem_liquida']),
            )
            for _, row in comp_groups.iterrows()
        ]

        # Top Teams by Attendance (Home games)
        team_groups = df.groupby('time_mandante').agg({
            'publico_total': 'mean',
            'ticket_medio': 'mean',
            'margem_liquida': 'mean',
            'id_jogo_cbf': 'count',
        }).reset_index()
        team_groups = team_groups.sort_values('publico_total', ascending=False).head(10)

        top_teams_by_attendance = [
            TeamStats(
                team_name=row['time_mandante'],
                average_attendance=int(row['publico_total']),
                average_ticket_price=float(row['ticket_medio']),
                average_net_margin=float(row['margem_liquida']),
                total_matches=int(row['id_jogo_cbf']),
            )
            for _, row in team_groups.iterrows()
        ]

        # Top Stadiums
        stadium_groups = df.groupby('estadio').agg({
            'publico_total': 'mean',
            'ticket_medio': 'mean',
            'id_jogo_cbf': 'count',
        }).reset_index()
        stadium_groups = stadium_groups.sort_values('publico_total', ascending=False).head(10)

        top_stadiums = [
            StadiumStats(
                stadium_name=row['estadio'],
                average_attendance=int(row['publico_total']),
                average_ticket_price=float(row['ticket_medio']),
                total_matches=int(row['id_jogo_cbf']),
            )
            for _, row in stadium_groups.iterrows()
        ]

        # Top Matches
        top_matches = []

        # Top by attendance
        top_attendance = df.nlargest(5, 'publico_total')
        for _, row in top_attendance.iterrows():
            top_matches.append(
                TopMatch(
                    id_jogo_cbf=row['id_jogo_cbf'],
                    data_jogo=pd.to_datetime(row['data_jogo']).date(),
                    time_mandante=row['time_mandante'],
                    time_visitante=row['time_visitante'],
                    estadio=row['estadio'],
                    value=float(row['publico_total']),
                    metric="attendance",
                )
            )

        # Top by revenue
        top_revenue = df.nlargest(5, 'receita_total')
        for _, row in top_revenue.iterrows():
            top_matches.append(
                TopMatch(
                    id_jogo_cbf=row['id_jogo_cbf'],
                    data_jogo=pd.to_datetime(row['data_jogo']).date(),
                    time_mandante=row['time_mandante'],
                    time_visitante=row['time_visitante'],
                    estadio=row['estadio'],
                    value=float(row['receita_total']),
                    metric="revenue",
                )
            )

        return AnalyticsResponse(
            general_stats=general_stats,
            competition_summary=competition_summary,
            top_teams_by_attendance=top_teams_by_attendance,
            top_stadiums=top_stadiums,
            top_matches=top_matches,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")


@router.get("/matches", response_model=List[MatchDetail])
async def get_matches(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    competition: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    stadium: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Get list of matches with filters"""
    try:
        db = SupabaseDatabase()

        # Build query
        query = db.client.table("jogos_resumo").select("*")

        if start_date:
            query = query.gte("data_jogo", start_date.isoformat())
        if end_date:
            query = query.lte("data_jogo", end_date.isoformat())
        if competition:
            query = query.eq("competicao", competition)
        if team:
            query = query.or_(f"time_mandante.eq.{team},time_visitante.eq.{team}")
        if stadium:
            query = query.eq("estadio", stadium)
        if year:
            query = query.gte("data_jogo", f"{year}-01-01").lte("data_jogo", f"{year}-12-31")

        # Apply limit and order
        query = query.order("data_jogo", desc=True).limit(limit)

        response = query.execute()
        matches = response.data

        return [
            MatchDetail(
                id_jogo_cbf=m['id_jogo_cbf'],
                data_jogo=pd.to_datetime(m['data_jogo']).date(),
                hora_inicio=m.get('hora_inicio'),
                competicao=m['competicao'],
                time_mandante=m['time_mandante'],
                time_visitante=m['time_visitante'],
                estadio=m['estadio'],
                cidade=m.get('cidade'),
                uf=m.get('uf'),
                placar_mandante=m.get('placar_mandante'),
                placar_visitante=m.get('placar_visitante'),
                publico_total=m['publico_total'],
                publico_pagante=m['publico_pagante'],
                publico_nao_pagante=m['publico_nao_pagante'],
                receita_total=m['receita_total'],
                despesa_total=m['despesa_total'],
                saldo=m['saldo'],
                preco_ingresso_medio=m.get('preco_ingresso_medio'),
                processado_em=pd.to_datetime(m['processado_em']) if m.get('processado_em') else None,
            )
            for m in matches
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching matches: {str(e)}")


@router.get("/matches/{id_jogo_cbf}", response_model=MatchDetailResponse)
async def get_match_detail(id_jogo_cbf: str):
    """Get detailed information for a specific match"""
    try:
        db = SupabaseDatabase()

        # Get match
        match_data = db.get_match(id_jogo_cbf)
        if not match_data:
            raise HTTPException(status_code=404, detail="Match not found")

        # Get revenues
        revenues_data = db.get_revenue_details(id_jogo_cbf)

        # Get expenses
        expenses_data = db.get_expense_details(id_jogo_cbf)

        match = MatchDetail(
            id_jogo_cbf=match_data['id_jogo_cbf'],
            data_jogo=pd.to_datetime(match_data['data_jogo']).date(),
            hora_inicio=match_data.get('hora_inicio'),
            competicao=match_data['competicao'],
            time_mandante=match_data['time_mandante'],
            time_visitante=match_data['time_visitante'],
            estadio=match_data['estadio'],
            cidade=match_data.get('cidade'),
            uf=match_data.get('uf'),
            placar_mandante=match_data.get('placar_mandante'),
            placar_visitante=match_data.get('placar_visitante'),
            publico_total=match_data['publico_total'],
            publico_pagante=match_data['publico_pagante'],
            publico_nao_pagante=match_data['publico_nao_pagante'],
            receita_total=match_data['receita_total'],
            despesa_total=match_data['despesa_total'],
            saldo=match_data['saldo'],
            preco_ingresso_medio=match_data.get('preco_ingresso_medio'),
            processado_em=pd.to_datetime(match_data['processado_em']) if match_data.get('processado_em') else None,
        )

        revenues = [
            RevenueDetail(
                categoria=r['categoria'],
                subcategoria=r.get('subcategoria'),
                valor=r['valor'],
            )
            for r in revenues_data
        ]

        expenses = [
            ExpenseDetail(
                categoria=e['categoria'],
                subcategoria=e.get('subcategoria'),
                valor=e['valor'],
            )
            for e in expenses_data
        ]

        return MatchDetailResponse(
            match=match,
            revenues=revenues,
            expenses=expenses,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching match details: {str(e)}")


@router.get("/filters/competitions")
async def get_competitions():
    """Get list of available competitions"""
    try:
        db = SupabaseDatabase()
        response = db.client.table("jogos_resumo").select("competicao").execute()

        competitions = list(set([m['competicao'] for m in response.data if m.get('competicao')]))
        return sorted(competitions)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching competitions: {str(e)}")


@router.get("/filters/teams")
async def get_teams():
    """Get list of available teams"""
    try:
        db = SupabaseDatabase()
        response = db.client.table("jogos_resumo").select("time_mandante,time_visitante").execute()

        teams = set()
        for m in response.data:
            if m.get('time_mandante'):
                teams.add(m['time_mandante'])
            if m.get('time_visitante'):
                teams.add(m['time_visitante'])

        return sorted(list(teams))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching teams: {str(e)}")


@router.get("/filters/stadiums")
async def get_stadiums():
    """Get list of available stadiums"""
    try:
        db = SupabaseDatabase()
        response = db.client.table("jogos_resumo").select("estadio").execute()

        stadiums = list(set([m['estadio'] for m in response.data if m.get('estadio')]))
        return sorted(stadiums)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stadiums: {str(e)}")
