import { useState, useRef } from 'react'
import { Upload, X } from 'lucide-react'
import { uploadFile, createTask, getTask } from '../api/client'
import type { TaskResponse } from '../types'

export default function SplitPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [pageRange, setPageRange] = useState('all')
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

  const handleClearFile = () => {
    setFile(null)
    setTask(null)
    setError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

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
        <div className="drop-zone-wrap">
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
          <button
            className={`drop-zone-remove${file ? ' visible' : ''}`}
            onClick={handleClearFile}
            title="移除文件"
            type="button"
          >
            <X size={14} />
          </button>
        </div>

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
