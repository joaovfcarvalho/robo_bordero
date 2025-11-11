import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../api/client'
import { format } from 'date-fns'
import { Users, DollarSign, TrendingUp, BarChart3 } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function formatCurrency(value: number) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('pt-BR').format(value)
}

export default function Dashboard() {
  const [filters, setFilters] = useState({
    competition: '',
    team: '',
  })

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', filters],
    queryFn: () => analyticsApi.getOverview(filters),
  })

  const { data: competitions } = useQuery({
    queryKey: ['competitions'],
    queryFn: () => analyticsApi.getCompetitions(),
  })

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: () => analyticsApi.getTeams(),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!analytics) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No data available</p>
      </div>
    )
  }

  const { general_stats, competition_summary, top_teams_by_attendance, top_stadiums } = analytics

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h2>
        <p className="mt-2 text-gray-600">
          Análise financeira de borderôs da CBF
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Competição
            </label>
            <select
              value={filters.competition}
              onChange={(e) => setFilters({ ...filters, competition: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Todas</option>
              {competitions?.map((comp) => (
                <option key={comp} value={comp}>
                  {comp}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Time
            </label>
            <select
              value={filters.team}
              onChange={(e) => setFilters({ ...filters, team: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Todos</option>
              {teams?.map((team) => (
                <option key={team} value={team}>
                  {team}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total de Jogos</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {formatNumber(general_stats.total_matches)}
              </p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <BarChart3 className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Público Total</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {formatNumber(general_stats.total_attendance)}
              </p>
            </div>
            <div className="p-3 bg-green-100 rounded-full">
              <Users className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Receita Total</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {formatCurrency(general_stats.total_revenue)}
              </p>
            </div>
            <div className="p-3 bg-yellow-100 rounded-full">
              <DollarSign className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Ticket Médio</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {formatCurrency(general_stats.average_ticket_price)}
              </p>
            </div>
            <div className="p-3 bg-purple-100 rounded-full">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Competition Summary */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Resumo por Competição
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={competition_summary}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="competicao" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'total_revenue') return formatCurrency(value)
                return formatNumber(value)
              }}
            />
            <Legend />
            <Bar yAxisId="left" dataKey="total_games" fill="#0ea5e9" name="Jogos" />
            <Bar yAxisId="right" dataKey="total_attendance" fill="#10b981" name="Público" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Teams */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Top Times por Público Médio
          </h3>
          <div className="space-y-3">
            {top_teams_by_attendance.slice(0, 5).map((team, index) => (
              <div key={team.team_name} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-lg font-bold text-gray-400 w-6">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">{team.team_name}</p>
                    <p className="text-sm text-gray-500">
                      {formatNumber(team.total_matches)} jogos
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-gray-900">
                    {formatNumber(team.average_attendance)}
                  </p>
                  <p className="text-sm text-gray-500">público médio</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Top Estádios
          </h3>
          <div className="space-y-3">
            {top_stadiums.slice(0, 5).map((stadium, index) => (
              <div key={stadium.stadium_name} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-lg font-bold text-gray-400 w-6">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">{stadium.stadium_name}</p>
                    <p className="text-sm text-gray-500">
                      {formatNumber(stadium.total_matches)} jogos
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-gray-900">
                    {formatNumber(stadium.average_attendance)}
                  </p>
                  <p className="text-sm text-gray-500">público médio</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
