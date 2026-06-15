import { useState } from 'react'
import { uploadFile, createTask, getTask } from '../api/client'
import type { TaskResponse } from '../types'

export default function SplitPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [pageRange, setPageRange] = useState('all')
  const [uploading, setUploading] = useState(false)
  const [task, setTask] = useState<TaskResponse | null>(null)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!file) return
    setError('')
    setUploading(true)
    try {
      const { file_id } = await uploadFile(file)
      const created = await createTask('split_pdf', [file_id], { page_range: pageRange })
      setTask(created)

      const poll = setInterval(async () => {
        const updated = await getTask(created.task_id)
        if (updated.status === 'succeeded' || updated.status === 'failed') {
          clearInterval(poll)
          setTask(updated)
        }
      }, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <section className="page">
      <h1>PDF 按页拆分</h1>
      <p className="text-muted">按页码或页码范围拆分 PDF，每页输出一个独立的 PDF 文件并打包为 ZIP。</p>

      <div className="form-card">
        <label className="form-label">选择 PDF 文件</label>
        <input type="file" accept=".pdf,application/pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />

        <label className="form-label">页码范围（如 all、1-5、1,3,5）</label>
        <input value={pageRange} onChange={(e) => setPageRange(e.target.value)} />

        <button className="btn" disabled={!file || uploading} onClick={handleSubmit}>
          {uploading ? '上传中...' : '开始拆分'}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {task && (
        <div className="result-card">
          <p>状态：{task.status}</p>
          {task.status === 'succeeded' && task.output_files.length > 0 && (
            <a href={`/api/files/${task.output_files[0].file_id}/download`} className="btn" download>
              下载 ZIP
            </a>
          )}
        </div>
      )}
    </section>
  )
}
