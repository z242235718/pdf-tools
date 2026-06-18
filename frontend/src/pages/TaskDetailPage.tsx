import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getTask } from '../api/client'
import { formatTime } from '../utils/formatTime'
import type { TaskResponse } from '../types'

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const [task, setTask] = useState<TaskResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!taskId) return
    getTask(Number(taskId))
      .then(setTask)
      .catch((err) => setError(err.message))
  }, [taskId])

  if (error) return <div className="error-msg">{error}</div>
  if (!task) return <p>加载中...</p>

  return (
    <section className="page">
      <h1>任务详情</h1>
      <dl className="detail-list">
        <dt>任务 ID</dt>
        <dd>{task.task_id}</dd>

        <dt>任务名称</dt>
        <dd>{task.task_name || '-'}</dd>

        <dt>工具类型</dt>
        <dd>{task.tool_type}</dd>

        <dt>原文件名称</dt>
        <dd>
          {task.input_files.length > 0
            ? task.input_files.map((f) => f.original_name).join('、')
            : '-'}
        </dd>

        <dt>状态</dt>
        <dd>
          <span className={`status-badge status-${task.status}`}>{task.status}</span>
        </dd>

        <dt>进度</dt>
        <dd>{task.progress}%</dd>

        <dt>创建时间</dt>
        <dd>{formatTime(task.created_at)}</dd>

        <dt>完成时间</dt>
        <dd>{formatTime(task.finished_at)}</dd>

        {task.error_message && (
          <>
            <dt>错误信息</dt>
            <dd className="error-msg">{task.error_message}</dd>
          </>
        )}

        {task.output_files.length > 0 && (
          <>
            <dt>输出文件</dt>
            <dd>
              {task.output_files.map((f) => (
                <div key={f.file_id} style={{ marginBottom: 4 }}>
                  <a href={`/api/files/${f.file_id}/download`} download>
                    {f.filename}
                  </a>
                </div>
              ))}
            </dd>
          </>
        )}
      </dl>
    </section>
  )
}
