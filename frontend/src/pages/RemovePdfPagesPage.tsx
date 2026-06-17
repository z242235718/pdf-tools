import { useState, useRef } from 'react'
import { Upload } from 'lucide-react'
import { uploadFile, createTask, getTask } from '../api/client'
import type { TaskResponse } from '../types'

export default function RemovePdfPagesPage() {
  const [file, setFile] = useState<File | null>(null)
  const [deletePages, setDeletePages] = useState('')
  const [uploading, setUploading] = useState(false)
  const [task, setTask] = useState<TaskResponse | null>(null)
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDropZoneClick = () => fileInputRef.current?.click()

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files?.[0] ?? null
    if (f && f.type !== 'application/pdf') {
      setError('请拖拽 PDF 文件')
      return
    }
    setFile(f)
    setTask(null)
    setError('')
  }

  const handleSubmit = async () => {
    if (!file || !deletePages) return
    setError('')
    setUploading(true)
    try {
      const { file_id } = await uploadFile(file)
      const created = await createTask('remove_pdf_pages', [file_id], { delete_pages: deletePages })
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
      <h1>删除 PDF 指定页</h1>
      <p className="text-muted">删除 PDF 中的指定页面，至少保留一页。</p>

      <div className="form-card">
        <label className="form-label">选择 PDF 文件</label>
        <div
          className={`drop-zone${isDragging ? ' dragging' : ''}${file ? ' has-file' : ''}`}
          onClick={handleDropZoneClick}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); setTask(null); setError('') }}
            hidden
          />
          <Upload size={24} className="drop-zone-icon" />
          <span className="drop-zone-text">
            {file ? file.name : '点击或拖拽 PDF 文件到此处'}
          </span>
        </div>

        <label className="form-label">要删除的页码（如 2,4-6）</label>
        <input value={deletePages} onChange={(e) => setDeletePages(e.target.value)} placeholder="2,4-6" />

        <button className="btn" disabled={!file || !deletePages || uploading} onClick={handleSubmit}>
          {uploading ? '上传中...' : '删除页面'}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {task && (
        <div className="result-card">
          <p>状态：{task.status}</p>
          {task.status === 'succeeded' && task.output_files.length > 0 && (
            <a href={`/api/files/${task.output_files[0].file_id}/download`} className="btn" download>
              下载结果
            </a>
          )}
        </div>
      )}
    </section>
  )
}
