import { useState } from 'react'
import { Search, ExternalLink } from 'lucide-react'

interface TraceResult {
  fingerprint_id: string
  visible_text: string | null
  metadata_payload: string | null
  verify_url: string | null
  source_file_id: number
  output_file_id: number | null
  task_id: number | null
  created_at: string | null
}

export default function TraceQueryPage() {
  const [fp, setFp] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TraceResult | null>(null)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!fp.trim()) return
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const res = await fetch('/api/trace/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fingerprint_id: fp.trim() }),
      })
      if (!res.ok) {
        if (res.status === 404) throw new Error('未找到该指纹记录')
        throw new Error(`查询失败 (${res.status})`)
      }
      const data: TraceResult = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '查询失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="page">
      <h1>溯源查询</h1>
      <p className="text-muted">
        输入文件中的指纹 ID，查询 PDF 的授权来源和分发信息。
      </p>

      <form className="form-card" onSubmit={handleSubmit}>
        <label className="form-label">指纹 ID</label>
        <input
          type="text"
          value={fp}
          onChange={(e) => setFp(e.target.value)}
          placeholder="输入指纹 ID"
        />
        <button
          className="btn"
          type="submit"
          disabled={!fp.trim() || loading}
        >
          <Search size={16} style={{ marginRight: 6 }} />
          {loading ? '查询中...' : '查询'}
        </button>
      </form>

      {error && <div className="error-msg">{error}</div>}

      {result && (
        <div className="result-card">
          <h3>查询结果</h3>
          <table className="trace-table">
            <tbody>
              <tr>
                <td className="trace-label">指纹 ID</td>
                <td className="trace-value">{result.fingerprint_id}</td>
              </tr>
              <tr>
                <td className="trace-label">授权信息</td>
                <td className="trace-value">{result.visible_text ?? '-'}</td>
              </tr>
              <tr>
                <td className="trace-label">生成时间</td>
                <td className="trace-value">{result.created_at ?? '-'}</td>
              </tr>
              <tr>
                <td className="trace-label">关联任务</td>
                <td className="trace-value">
                  {result.task_id != null
                    ? <a href={`/task/${result.task_id}`}>任务 #{result.task_id}</a>
                    : '-'}
                </td>
              </tr>
              {result.verify_url && (
                <tr>
                  <td className="trace-label">验证链接</td>
                  <td className="trace-value">
                    <a href={result.verify_url} target="_blank" rel="noopener noreferrer">
                      打开 <ExternalLink size={12} />
                    </a>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
