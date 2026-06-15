import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getTask } from '../api/client'
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
        <dt>工具类型</dt>
        <dd>{task.tool_type}</dd>
        <dt>状态</dt>
        <dd>{task.status}</dd>
        <dt>进度</dt>
        <dd>{task.progress}%</dd>
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
                <a key={f.file_id} href={`/api/files/${f.file_id}/download`} download>
                  {f.filename}
                </a>
              ))}
            </dd>
          </>
        )}
      </dl>
    </section>
  )
}
