import { useState, useEffect, useRef } from 'react'
import { X, ChevronUp, ChevronDown } from 'lucide-react'
import { uploadFile, createTask, getTask } from '../api/client'
import type { TaskResponse, ImageItem } from '../types'

export default function ImagesToPdfPage() {
  const [imageItems, setImageItems] = useState<ImageItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [task, setTask] = useState<TaskResponse | null>(null)
  const [error, setError] = useState('')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const dragIndexRef = useRef<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Keep ref updated so unmount cleanup has the latest URLs
  const previewUrlsRef = useRef<string[]>([])
  useEffect(() => {
    previewUrlsRef.current = imageItems.map((item) => item.previewUrl)
  })
  // Only revoke remaining URLs on unmount
  useEffect(() => {
    return () => {
      previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    // Revoke previous previews
    imageItems.forEach((item) => URL.revokeObjectURL(item.previewUrl))

    const items: ImageItem[] = Array.from(files).map((file) => ({
      id: crypto.randomUUID(),
      file,
      previewUrl: URL.createObjectURL(file),
    }))
    setImageItems(items)
    setTask(null)
    setError('')

    // Reset input value so onChange fires again for the same files
    // and the native tooltip doesn't show stale counts
    e.target.value = ''
  }

  const handleRemove = (id: string) => {
    const item = imageItems.find((i) => i.id === id)
    if (item) URL.revokeObjectURL(item.previewUrl)
    setImageItems((prev) => prev.filter((i) => i.id !== id))
  }

  const handleClearAll = () => {
    imageItems.forEach((item) => URL.revokeObjectURL(item.previewUrl))
    setImageItems([])
    setTask(null)
    setError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleMoveUp = (index: number) => {
    if (index === 0) return
    setImageItems((prev) => {
      const next = [...prev]
      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
      return next
    })
  }

  const handleMoveDown = (index: number) => {
    if (index === imageItems.length - 1) return
    setImageItems((prev) => {
      const next = [...prev]
      ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
      return next
    })
  }

  const handleDragStart = (_e: React.DragEvent, index: number) => {
    dragIndexRef.current = index
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault()
    const fromIndex = dragIndexRef.current
    if (fromIndex === null || fromIndex === dropIndex) return

    setImageItems((prev) => {
      const next = [...prev]
      const [moved] = next.splice(fromIndex, 1)
      next.splice(dropIndex, 0, moved)
      return next
    })
    dragIndexRef.current = null
  }

  const handleDragEnd = () => {
    dragIndexRef.current = null
  }

  const handleSubmit = async () => {
    if (imageItems.length === 0) return
    setError('')
    setUploading(true)
    try {
      const ids: number[] = []
      for (const item of imageItems) {
        const { file_id } = await uploadFile(item.file)
        ids.push(file_id)
      }
      const created = await createTask('images_to_pdf', ids, { merge_mode: 'single_pdf' })
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
      <h1>图片转 PDF</h1>
      <p className="text-muted">上传一张或多张图片，合并为 PDF 文件。拖拽缩略图可调整顺序。</p>

      <div className="form-card form-card-wide">
        <label className="form-label">选择图片</label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
        />

        {imageItems.length > 0 && (
          <div className="image-grid">
            {imageItems.map((item, index) => (
              <div
                key={item.id}
                className="image-thumb"
                draggable
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, index)}
                onDragEnd={handleDragEnd}
              >
                <img src={item.previewUrl} alt={item.file.name} onClick={() => setPreviewUrl(item.previewUrl)} />
                <span className="thumb-order">{index + 1}</span>
                <button
                  className="thumb-remove"
                  onClick={() => handleRemove(item.id)}
                  title="移除"
                  type="button"
                >
                  <X size={14} />
                </button>
                <div className="thumb-arrows">
                  <button
                    className="thumb-arrow"
                    disabled={index === 0}
                    onClick={() => handleMoveUp(index)}
                    title="上移"
                    type="button"
                  >
                    <ChevronUp size={14} />
                  </button>
                  <button
                    className="thumb-arrow"
                    disabled={index === imageItems.length - 1}
                    onClick={() => handleMoveDown(index)}
                    title="下移"
                    type="button"
                  >
                    <ChevronDown size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="form-actions">
          <button
            className="btn"
            disabled={imageItems.length === 0 || uploading}
            onClick={handleSubmit}
          >
            {uploading ? '上传中...' : '生成 PDF'}
          </button>
          {imageItems.length > 0 && (
            <button className="btn btn-secondary" onClick={handleClearAll} type="button">
              清除全部
            </button>
          )}
        </div>
      </div>

      {previewUrl && (
        <div className="lightbox" onClick={() => { setPreviewUrl(null); setZoom(1) }}>
          <button className="lightbox-close-btn" onClick={() => { setPreviewUrl(null); setZoom(1) }} type="button">
            <X size={20} />
          </button>
          <div className="lightbox-body" onClick={(e) => e.stopPropagation()}>
            <img
              src={previewUrl}
              alt="预览"
              style={{ transform: `scale(${zoom})` }}
              className="lightbox-img"
              onClick={() => setZoom((z) => (z >= 3 ? 1 : z + 1))}
              onWheel={(e) => {
                e.preventDefault()
                setZoom((z) => Math.max(0.5, Math.min(5, z - e.deltaY * 0.002)))
              }}
            />
          </div>
          <div className="lightbox-toolbar" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.5))} type="button">−</button>
            <span className="lightbox-zoom-label">{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom((z) => Math.min(5, z + 0.5))} type="button">+</button>
            <button onClick={() => setZoom(1)} type="button">重置</button>
            <button className="lightbox-close-toolbar" onClick={() => { setPreviewUrl(null); setZoom(1) }} type="button">
              关闭
            </button>
          </div>
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      {task && (
        <div className="result-card">
          <p>状态：{task.status}</p>
          {task.status === 'succeeded' && task.output_files.length > 0 && (
            <a
              href={`/api/files/${task.output_files[0].file_id}/download`}
              className="btn"
              download
            >
              下载结果
            </a>
          )}
        </div>
      )}
    </section>
  )
}
