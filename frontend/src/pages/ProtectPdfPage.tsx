import { useState, useRef } from 'react'
import { Upload, Download } from 'lucide-react'
import { uploadFile, createTask, getTask } from '../api/client'
import type { TaskResponse } from '../types'

export default function ProtectPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [visibleText, setVisibleText] = useState('')
  const [addQrcode, setAddQrcode] = useState(true)
  const [setPermissions, setSetPermissions] = useState(false)
  const [pageRange, setPageRange] = useState('all')
  const [uploading, setUploading] = useState(false)
  const [task, setTask] = useState<TaskResponse | null>(null)
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null
    if (f && f.type !== 'application/pdf') {
      setError('请选择 PDF 文件')
      return
    }
    setFile(f)
    setTask(null)
    setError('')
  }

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
    if (!file) return
    if (!visibleText.trim()) {
      setError('请输入授权信息')
      return
    }
    setError('')
    setUploading(true)
    try {
      const { file_id } = await uploadFile(file)
      const created = await createTask('protect_pdf', [file_id], {
        visible_text: visibleText,
        add_qrcode: addQrcode,
        set_permissions: setPermissions,
        page_range: pageRange,
      })
      setTask(created)

      const poll = setInterval(async () => {
        const updated = await getTask(created.task_id)
        if (updated.status === 'succeeded' || updated.status === 'failed') {
          clearInterval(poll)
          setTask(updated)
        }
      }, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setUploading(false)
    }
  }

  return (
    <section className="page">
      <h1>版权保护</h1>
      <p className="text-muted">
        为 PDF 添加可追踪的版权指纹。系统会在每页底部标注授权信息，
        并将唯一指纹写入文件元数据，实现分发溯源。
      </p>

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
            onChange={handleFileChange}
            hidden
          />
          <Upload size={24} className="drop-zone-icon" />
          <span className="drop-zone-text">
            {file ? file.name : '点击或拖拽 PDF 文件到此处'}
          </span>
        </div>

        <label className="form-label">授权信息</label>
        <input
          type="text"
          value={visibleText}
          onChange={(e) => setVisibleText(e.target.value)}
          placeholder="例如：授权给：张三"
        />

        <div className="slider-row">
          <label className="form-label">页码范围</label>
          <input
            value={pageRange}
            onChange={(e) => setPageRange(e.target.value)}
            placeholder="all"
          />
        </div>

        <div className="checkbox-row">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={addQrcode}
              onChange={(e) => setAddQrcode(e.target.checked)}
            />
            添加二维码（扫描后可溯源验证）
          </label>
        </div>

        <div className="checkbox-row">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={setPermissions}
              onChange={(e) => setSetPermissions(e.target.checked)}
            />
            设置权限保护（限制打印和复制）
          </label>
        </div>

        <button
          className="btn"
          disabled={!file || !visibleText.trim() || uploading}
          onClick={handleSubmit}
        >
          {uploading ? '处理中...' : '开始保护'}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {task && (
        <div className="result-card">
          <p>
            <strong>状态：</strong>
            {task.status === 'succeeded'
              ? '✅ 保护成功'
              : task.status === 'failed'
                ? '❌ 保护失败'
                : task.status}
          </p>
          {task.warnings && task.warnings.length > 0 && (
            <div className="warning-msg">
              {task.warnings.map((w, i) => (
                <p key={i}>{w}</p>
              ))}
            </div>
          )}
          {task.status === 'succeeded' && task.output_files.length > 0 && (
            <a
              href={`/api/files/${task.output_files[0].file_id}/download`}
              className="btn"
              download
            >
              <Download size={16} style={{ marginRight: 6 }} />
              下载受保护的 PDF
            </a>
          )}
          {task.status === 'succeeded' && (
            <p className="text-muted" style={{ marginTop: 8, fontSize: 13 }}>
              指纹 ID 已嵌入文件元数据。可前往
              <a href="/trace-query"> 溯源查询 </a>
              页面验证。
            </p>
          )}
          {task.error_message && (
            <p className="error-msg">错误：{task.error_message}</p>
          )}
        </div>
      )}
    </section>
  )
}
