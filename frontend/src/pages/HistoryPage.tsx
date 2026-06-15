import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listTasks } from '../api/client'
import type { TaskResponse } from '../types'

export default function HistoryPage() {
  const [tasks, setTasks] = useState<TaskResponse[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    listTasks()
      .then(setTasks)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <div className="error-msg">{error}</div>

  return (
    <section className="page">
      <h1>历史任务</h1>
      <p className="text-muted">最近处理的任务列表。</p>

      {tasks.length === 0 && <p>暂无任务记录。</p>}

      <table className="task-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>工具</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.task_id}>
              <td>{t.task_id}</td>
              <td>{t.tool_type}</td>
              <td>
                <span className={`status-badge status-${t.status}`}>{t.status}</span>
              </td>
              <td>{t.created_at ?? '-'}</td>
              <td>
                <Link to={`/task/${t.task_id}`}>查看详情</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
