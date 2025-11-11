import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { pdfsApi, adminApi } from '../api/client'
import { format } from 'date-fns'
import {
  FileText,
  Download,
  RefreshCw,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  Play,
} from 'lucide-react'
import type { PDFInfo, ScrapeRequest, BulkScrapeRequest } from '../types'

function formatDate(dateStr?: string) {
  if (!dateStr) return 'N/A'
  try {
    return format(new Date(dateStr), 'dd/MM/yyyy')
  } catch {
    return dateStr
  }
}

export default function PDFManager() {
  const queryClient = useQueryClient()
  const [year, setYear] = useState(new Date().getFullYear())
  const [competition, setCompetition] = useState('')
  const [showUnprocessedOnly, setShowUnprocessedOnly] = useState(false)

  const { data: pdfs, isLoading } = useQuery({
    queryKey: ['pdfs', year, competition, showUnprocessedOnly],
    queryFn: () =>
      pdfsApi.getAvailable({
        year,
        competition: competition || undefined,
        unprocessed_only: showUnprocessedOnly,
      }),
  })

  const { data: queueStatus } = useQuery({
    queryKey: ['queue-status'],
    queryFn: () => pdfsApi.getQueueStatus(),
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const { data: adminStats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => adminApi.getStats(),
  })

  const scrapeMutation = useMutation({
    mutationFn: (data: ScrapeRequest) => pdfsApi.scrapePDF(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pdfs'] })
      queryClient.invalidateQueries({ queryKey: ['queue-status'] })
    },
  })

  const bulkScrapeMutation = useMutation({
    mutationFn: (data: BulkScrapeRequest) => adminApi.bulkScrape(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pdfs'] })
      queryClient.invalidateQueries({ queryKey: ['queue-status'] })
    },
  })

  const retryMutation = useMutation({
    mutationFn: (id: string) => pdfsApi.retryFailed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue-status'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => pdfsApi.removeFromQueue(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue-status'] })
    },
  })

  const handleScrapePDF = (pdf: PDFInfo) => {
    if (confirm(`Processar PDF: ${pdf.id_jogo_cbf}?`)) {
      scrapeMutation.mutate({
        id_jogo_cbf: pdf.id_jogo_cbf,
        pdf_url: pdf.pdf_url,
        competicao: pdf.competicao,
        ano: pdf.ano,
        force_reprocess: pdf.processed,
      })
    }
  }

  const handleBulkScrape = () => {
    if (
      confirm(
        `Iniciar processamento em lote para o ano ${year}? Isso pode levar vários minutos.`
      )
    ) {
      bulkScrapeMutation.mutate({
        year,
        competition_codes: competition ? [competition] : undefined,
      })
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">PDF Manager</h2>
        <p className="mt-2 text-gray-600">
          Gerenciar e processar borderôs da CBF
        </p>
      </div>

      {/* Admin Stats */}
      {adminStats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <p className="text-sm text-gray-600">Total Jogos</p>
            <p className="text-2xl font-bold text-gray-900">{adminStats.total_matches}</p>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <p className="text-sm text-gray-600">PDFs Armazenados</p>
            <p className="text-2xl font-bold text-gray-900">{adminStats.pdfs_stored}</p>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-yellow-400">
            <p className="text-sm text-gray-600">Pendentes</p>
            <p className="text-2xl font-bold text-yellow-600">{adminStats.queue_pending}</p>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-blue-400">
            <p className="text-sm text-gray-600">Processando</p>
            <p className="text-2xl font-bold text-blue-600">{adminStats.queue_processing}</p>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-red-400">
            <p className="text-sm text-gray-600">Falhas</p>
            <p className="text-2xl font-bold text-red-600">{adminStats.queue_failed}</p>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <p className="text-sm text-gray-600">Total Fila</p>
            <p className="text-2xl font-bold text-gray-900">{adminStats.total_queue_items}</p>
          </div>
        </div>
      )}

      {/* Queue Status */}
      {queueStatus && queueStatus.recent_items.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Fila de Processamento
          </h3>
          <div className="space-y-2">
            {queueStatus.recent_items.slice(0, 5).map((item) => (
              <div
                key={item.id_jogo_cbf}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  {item.status === 'completed' && (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  )}
                  {item.status === 'failed' && (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  {item.status === 'processing' && (
                    <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
                  )}
                  {item.status === 'pending' && (
                    <Clock className="w-5 h-5 text-yellow-600" />
                  )}
                  <div>
                    <p className="font-medium text-gray-900">{item.id_jogo_cbf}</p>
                    <p className="text-sm text-gray-500">
                      {item.competicao} - {item.ano}
                    </p>
                    {item.ultimo_erro && (
                      <p className="text-sm text-red-600 mt-1">{item.ultimo_erro}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {item.status === 'failed' && (
                    <button
                      onClick={() => retryMutation.mutate(item.id_jogo_cbf)}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Retry
                    </button>
                  )}
                  <button
                    onClick={() => deleteMutation.mutate(item.id_jogo_cbf)}
                    className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters and Bulk Actions */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              {[2025, 2024, 2023].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Competição
            </label>
            <select
              value={competition}
              onChange={(e) => setCompetition(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todas</option>
              <option value="142">Brasileirão Série A (142)</option>
              <option value="424">Copa do Brasil (424)</option>
              <option value="242">Brasileirão Série B (242)</option>
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={showUnprocessedOnly}
                onChange={(e) => setShowUnprocessedOnly(e.target.checked)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">Apenas não processados</span>
            </label>
          </div>
        </div>

        <div className="flex space-x-2">
          <button
            onClick={handleBulkScrape}
            disabled={bulkScrapeMutation.isPending}
            className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            <Play className="w-4 h-4 mr-2" />
            Processar em Lote
          </button>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['pdfs'] })}
            className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Atualizar
          </button>
        </div>
      </div>

      {/* PDFs List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            PDFs Disponíveis ({pdfs?.length || 0})
          </h3>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : pdfs && pdfs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    ID do Jogo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Data
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Competição
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Times
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {pdfs.map((pdf) => (
                  <tr key={pdf.id_jogo_cbf}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {pdf.id_jogo_cbf}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(pdf.data_jogo)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {pdf.competicao}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {pdf.time_mandante && pdf.time_visitante
                        ? `${pdf.time_mandante} vs ${pdf.time_visitante}`
                        : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {pdf.processed ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Processado
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          <Clock className="w-3 h-3 mr-1" />
                          Pendente
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleScrapePDF(pdf)}
                          disabled={scrapeMutation.isPending}
                          className="inline-flex items-center px-3 py-1 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
                        >
                          <Download className="w-4 h-4 mr-1" />
                          {pdf.processed ? 'Reprocessar' : 'Processar'}
                        </button>
                        <a
                          href={pdf.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700"
                        >
                          <FileText className="w-4 h-4 mr-1" />
                          Ver PDF
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">Nenhum PDF encontrado</p>
          </div>
        )}
      </div>
    </div>
  )
}
