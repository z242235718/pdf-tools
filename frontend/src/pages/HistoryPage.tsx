import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Search, RotateCcw } from 'lucide-react'
import { listTasks } from '../api/client'
import { formatTime } from '../utils/formatTime'
import type { ListTasksParams } from '../api/client'
import type { TaskResponse } from '../types'

const STATUS_OPTIONS = [
  { value: 'pending', label: '等待中' },
  { value: 'running', label: '运行中' },
  { value: 'succeeded', label: '成功' },
  { value: 'failed', label: '失败' },
  { value: 'expired', label: '已过期' },
]

const PAGE_SIZE_OPTIONS = [20, 30, 50, 100]

export default function HistoryPage() {
  // ── Search / filter state ─────────────────────────────────────────────────
  const [searchTaskName, setSearchTaskName] = useState('')
  const [searchFileName, setSearchFileName] = useState('')
  const [searchDateFrom, setSearchDateFrom] = useState('')
  const [searchDateTo, setSearchDateTo] = useState('')
  const [searchStatuses, setSearchStatuses] = useState<string[]>([])

  // ── Pagination state ─────────────────────────────────────────────────────
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // ── Data state ────────────────────────────────────────────────────────────
  const [tasks, setTasks] = useState<TaskResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  // ── Fetch tasks ───────────────────────────────────────────────────────────
  const fetchTasks = useCallback(async (params: ListTasksParams) => {
    setLoading(true)
    setError('')
    try {
      const res = await listTasks(params)
      setTasks(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
      setTasks([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Build search params from current state ────────────────────────────────
  const buildParams = useCallback(
    (p: number, ps: number): ListTasksParams => {
      const params: ListTasksParams = {
        limit: ps,
        offset: (p - 1) * ps,
      }
      if (searchTaskName.trim()) params.task_name = searchTaskName.trim()
      if (searchFileName.trim()) params.file_name = searchFileName.trim()
      if (searchDateFrom) params.date_from = searchDateFrom
      if (searchDateTo) params.date_to = searchDateTo
      if (searchStatuses.length > 0) params.status = searchStatuses.join(',')
      return params
    },
    [searchTaskName, searchFileName, searchDateFrom, searchDateTo, searchStatuses],
  )

  // ── Initial load & refetch on page/pageSize change ───────────────────────
  useEffect(() => {
    fetchTasks(buildParams(page, pageSize))
  }, [page, pageSize, fetchTasks, buildParams])

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleSearch = () => {
    setPage(1)
    fetchTasks(buildParams(1, pageSize))
  }

  const handleReset = () => {
    setSearchTaskName('')
    setSearchFileName('')
    setSearchDateFrom('')
    setSearchDateTo('')
    setSearchStatuses([])
    setPage(1)
    fetchTasks(buildParams(1, pageSize))
  }

  const toggleStatus = (value: string) => {
    setSearchStatuses((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value],
    )
  }

  const goToPage = (p: number) => {
    if (p >= 1 && p <= totalPages) setPage(p)
  }

  // ── Render page numbers ──────────────────────────────────────────────────
  const renderPageNumbers = () => {
    const pages: (number | string)[] = []
    const maxVisible = 7

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
    } else {
      pages.push(1)
      const start = Math.max(2, page - 2)
      const end = Math.min(totalPages - 1, page + 2)

      if (start > 2) pages.push('...')
      for (let i = start; i <= end; i++) pages.push(i)
      if (end < totalPages - 1) pages.push('...')
      pages.push(totalPages)
    }

    return pages.map((p, idx) =>
      typeof p === 'string' ? (
        <span key={`ellipsis-${idx}`} className="page-ellipsis">…</span>
      ) : (
        <button
          key={p}
          className={`page-btn ${p === page ? 'page-btn-active' : ''}`}
          onClick={() => goToPage(p)}
          disabled={loading}
        >
          {p}
        </button>
      ),
    )
  }

  return (
    <section className="page">
      <h1>历史任务</h1>
      <p className="text-muted">查看和管理最近处理的任务。</p>

      {/* ── Search bar ─────────────────────────────────────────────────── */}
      <div className="search-bar">
        <div className="search-row">
          <div className="search-field">
            <label>任务名称</label>
            <input
              type="text"
              value={searchTaskName}
              onChange={(e) => setSearchTaskName(e.target.value)}
              placeholder="按任务名称搜索"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <div className="search-field">
            <label>原文件名称</label>
            <input
              type="text"
              value={searchFileName}
              onChange={(e) => setSearchFileName(e.target.value)}
              placeholder="按原文件名称搜索"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <div className="search-field">
            <label>开始日期</label>
            <input
              type="date"
              value={searchDateFrom}
              onChange={(e) => setSearchDateFrom(e.target.value)}
            />
          </div>
          <div className="search-field">
            <label>结束日期</label>
            <input
              type="date"
              value={searchDateTo}
              onChange={(e) => setSearchDateTo(e.target.value)}
            />
          </div>
        </div>
        <div className="search-row">
          <div className="search-field status-filter">
            <label>状态</label>
            <div className="status-checkboxes">
              {STATUS_OPTIONS.map((opt) => (
                <label key={opt.value} className="status-checkbox-label">
                  <input
                    type="checkbox"
                    checked={searchStatuses.includes(opt.value)}
                    onChange={() => toggleStatus(opt.value)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>
          <div className="search-actions">
            <button className="btn" onClick={handleSearch} disabled={loading}>
              <Search size={15} style={{ marginRight: 4 }} />
              搜索
            </button>
            <button className="btn btn-outline" onClick={handleReset} disabled={loading}>
              <RotateCcw size={15} style={{ marginRight: 4 }} />
              重置
            </button>
          </div>
        </div>
      </div>

      {/* ── Error ──────────────────────────────────────────────────────── */}
      {error && <div className="error-msg">{error}</div>}

      {/* ── Table ──────────────────────────────────────────────────────── */}
      <div className="task-table-wrap">
      <table className="task-table">
        <thead>
          <tr>
            <th>任务ID</th>
            <th>任务名称</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {loading && tasks.length === 0 ? (
            <tr>
              <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                加载中...
              </td>
            </tr>
          ) : tasks.length === 0 ? (
            <tr>
              <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                暂无任务记录。
              </td>
            </tr>
          ) : (
            tasks.map((t) => (
              <tr key={t.task_id}>
                <td>{t.task_id}</td>
                <td>{t.task_name || '-'}</td>
                <td>
                  <span className={`status-badge status-${t.status}`}>{t.status}</span>
                </td>
                <td>{formatTime(t.created_at)}</td>
                <td>
                  <Link to={`/task/${t.task_id}`}>查看详情</Link>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      </div>

      {/* ── Pagination ─────────────────────────────────────────────────── */}
      <div className="pagination-bar">
        <div className="pagination-info">
          共 {total} 条，每页
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value))
              setPage(1)
            }}
            disabled={loading}
          >
            {PAGE_SIZE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          条
        </div>
        <div className="pagination-controls">
          <button
            className="page-btn"
            onClick={() => goToPage(1)}
            disabled={page === 1 || loading}
            title="第一页"
          >
            &laquo;
          </button>
          <button
            className="page-btn"
            onClick={() => goToPage(page - 1)}
            disabled={page === 1 || loading}
            title="上一页"
          >
            &lsaquo;
          </button>
          {renderPageNumbers()}
          <button
            className="page-btn"
            onClick={() => goToPage(page + 1)}
            disabled={page === totalPages || loading}
            title="下一页"
          >
            &rsaquo;
          </button>
          <button
            className="page-btn"
            onClick={() => goToPage(totalPages)}
            disabled={page === totalPages || loading}
            title="最后一页"
          >
            &raquo;
          </button>
        </div>
      </div>
    </section>
  )
}
