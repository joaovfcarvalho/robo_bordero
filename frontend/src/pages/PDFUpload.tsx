import { useState } from 'react'
import { Upload, FileText, AlertCircle, CheckCircle, Loader } from 'lucide-react'
import { pdfsApi } from '../api/client'

export default function PDFUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [pdfUrl, setPdfUrl] = useState('')
  const [idJogo, setIdJogo] = useState('')
  const [competition, setCompetition] = useState('142')
  const [year, setYear] = useState(new Date().getFullYear().toString())
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setResult(null)
    }
  }

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!pdfUrl || !idJogo) {
      setResult({ success: false, message: 'Por favor, preencha todos os campos obrigatórios.' })
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const response = await pdfsApi.scrapePDF({
        id_jogo_cbf: idJogo,
        pdf_url: pdfUrl,
        competicao: competition,
        ano: parseInt(year),
        force_reprocess: true
      })

      setResult({
        success: response.success,
        message: response.message || 'PDF adicionado à fila de processamento com sucesso!'
      })

      // Clear form on success
      if (response.success) {
        setPdfUrl('')
        setIdJogo('')
      }
    } catch (error: any) {
      setResult({
        success: false,
        message: error.response?.data?.detail || 'Erro ao processar PDF. Tente novamente.'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Análise de PDF</h2>
        <p className="mt-2 text-gray-600">
          Envie um borderô da CBF para análise
        </p>
      </div>

      {/* URL Upload Form */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <FileText className="w-6 h-6 text-indigo-600" />
          <h3 className="text-xl font-semibold text-gray-900">Analisar Borderô por URL</h3>
        </div>

        <form onSubmit={handleUrlSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="idJogo" className="block text-sm font-medium text-gray-700 mb-1">
                ID do Jogo CBF *
              </label>
              <input
                type="text"
                id="idJogo"
                value={idJogo}
                onChange={(e) => setIdJogo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Ex: 1234567"
                required
              />
            </div>

            <div>
              <label htmlFor="competition" className="block text-sm font-medium text-gray-700 mb-1">
                Competição
              </label>
              <select
                id="competition"
                value={competition}
                onChange={(e) => setCompetition(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="142">Série A (142)</option>
                <option value="424">Copa do Brasil (424)</option>
                <option value="242">Série B (242)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="year" className="block text-sm font-medium text-gray-700 mb-1">
                Ano
              </label>
              <input
                type="number"
                id="year"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="2024"
                min="2020"
                max="2030"
              />
            </div>
          </div>

          <div>
            <label htmlFor="pdfUrl" className="block text-sm font-medium text-gray-700 mb-1">
              URL do PDF *
            </label>
            <input
              type="url"
              id="pdfUrl"
              value={pdfUrl}
              onChange={(e) => setPdfUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="https://conteudo.cbf.com.br/sumulas/..."
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Exemplo: https://conteudo.cbf.com.br/sumulas/2024/142_bordero_1234567.pdf
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <Loader className="w-5 h-5 animate-spin" />
                <span>Processando...</span>
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                <span>Analisar PDF</span>
              </>
            )}
          </button>
        </form>

        {/* Result Message */}
        {result && (
          <div className={`mt-4 p-4 rounded-lg flex items-start space-x-3 ${
            result.success
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}>
            {result.success ? (
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            )}
            <div>
              <p className={`text-sm font-medium ${
                result.success ? 'text-green-800' : 'text-red-800'
              }`}>
                {result.message}
              </p>
              {result.success && (
                <p className="mt-1 text-xs text-green-700">
                  O PDF está sendo processado. Você pode ver os resultados no Dashboard em alguns minutos.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-2">Como encontrar borderôs da CBF:</p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Acesse o site da CBF e encontre a súmula do jogo desejado</li>
              <li>O formato da URL é: https://conteudo.cbf.com.br/sumulas/[ANO]/[CODIGO_COMP]_bordero_[ID_JOGO].pdf</li>
              <li>Códigos de competição: 142 (Série A), 424 (Copa do Brasil), 242 (Série B)</li>
              <li>Cole a URL completa no campo acima e clique em "Analisar PDF"</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}
