import { useState, useEffect, useRef } from 'react'
import { Upload, Eye, Download } from 'lucide-react'
import { uploadFile, createTask, getTask } from '../api/client'
import type { TaskResponse } from '../types'

type WatermarkType = 'text' | 'image'

interface PreviewResponse {
  file_id: number
  page_count: number
  preview_image_url: string | null
}

const POSITIONS = [
  { value: 'center', label: '居中' },
  { value: 'top-left', label: '左上' },
  { value: 'top-center', label: '上中' },
  { value: 'top-right', label: '右上' },
  { value: 'left-center', label: '左中' },
  { value: 'right-center', label: '右中' },
  { value: 'bottom-left', label: '左下' },
  { value: 'bottom-center', label: '下中' },
  { value: 'bottom-right', label: '右下' },
]

const TEXT_TILE_MODES = [
  { value: 'single', label: '单个' },
  { value: 'full', label: '全页平铺' },
  { value: 'grid', label: '等距分布' },
  { value: 'dense', label: '密集形' },
]

const IMAGE_TILE_MODES = [
  { value: 'single', label: '单个' },
  { value: 'full', label: '全页平铺' },
  { value: 'grid', label: '等距分布' },
]

export default function WatermarkPdfPage() {
  const [watermarkType, setWatermarkType] = useState<WatermarkType>('text')

  // PDF file
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [pdfFileId, setPdfFileId] = useState<number | null>(null)

  // Text watermark params
  const [text, setText] = useState('内部资料')
  const [fontSize, setFontSize] = useState(32)
  const [color, setColor] = useState('#888888')

  // Image watermark params
  const [wmImageFile, setWmImageFile] = useState<File | null>(null)
  const [wmImageFileId, setWmImageFileId] = useState<number | null>(null)
  const [scale, setScale] = useState(0.5)

  // Common params
  const [opacity, setOpacity] = useState(0.25)
  const [rotation, setRotation] = useState(-30)
  const [position, setPosition] = useState('center')
  const [tileMode, setTileMode] = useState('full')
  const [gridAxis, setGridAxis] = useState<'x' | 'y'>('x')
  const [gridSpacing, setGridSpacing] = useState(2.0)
  const [tileSpacing, setTileSpacing] = useState(1.5)
  const [pageRange, setPageRange] = useState('all')

  // UI state
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [task, setTask] = useState<TaskResponse | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [isPdfDragging, setIsPdfDragging] = useState(false)
  const [isWmDragging, setIsWmDragging] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pdfFileInputRef = useRef<HTMLInputElement>(null)
  const wmFileInputRef = useRef<HTMLInputElement>(null)

  // ── Refs for latest params (avoids stale closure in async handlers) ──────
  const paramsRef = useRef({
    watermarkType: 'text' as WatermarkType,
    text: '内部资料',
    fontSize: 32,
    color: '#888888',
    wmImageFileId: null as number | null,
    scale: 0.5,
    opacity: 0.25,
    rotation: -30,
    position: 'center',
    tileMode: 'full',
    gridAxis: 'x' as 'x' | 'y',
    gridSpacing: 2.0,
    tileSpacing: 1.5,
    pageRange: 'all',
  })

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current !== null) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [])

  const buildParams = (): Record<string, unknown> => {
    const p = paramsRef.current
    // Dense mode uses raw opacity (不透明度); other modes invert transparency → opacity
    const common = {
      opacity: p.tileMode === 'dense' ? p.opacity : 1 - p.opacity,
      rotation: p.rotation,
      position: p.position,
      tile_mode: p.tileMode,
      page_range: p.pageRange,
      ...(p.tileMode === 'grid' ? { grid_axis: p.gridAxis, grid_spacing: p.gridSpacing } : {}),
      ...(p.tileMode === 'full' ? { tile_spacing: p.tileSpacing } : {}),
    }
    if (p.watermarkType === 'text') {
      return { watermark_type: 'text', text: p.text, font_size: p.fontSize, color: p.color, ...common }
    }
    return { watermark_type: 'image', watermark_file_id: p.wmImageFileId, scale: p.scale, ...common }
  }

  // ── Drag-and-drop handlers for PDF ───────────────────────────────────────
  const handlePdfDropZoneClick = () => pdfFileInputRef.current?.click()

  const handlePdfDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    setIsPdfDragging(true)
  }

  const handlePdfDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handlePdfDragLeave = () => {
    setIsPdfDragging(false)
  }

  const handlePdfDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsPdfDragging(false)
    const f = e.dataTransfer.files?.[0] ?? null
    if (f && f.type !== 'application/pdf') {
      setError('请拖拽 PDF 文件')
      return
    }
    setPdfFile(f)
    setPdfFileId(null)
    setPreviewUrl(null)
    setTask(null)
    setError('')
  }

  const handlePdfFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPdfFile(e.target.files?.[0] ?? null)
    setPdfFileId(null)
    setPreviewUrl(null)
    setTask(null)
  }

  // ── Drag-and-drop handlers for watermark image ──────────────────────────
  const handleWmDropZoneClick = () => wmFileInputRef.current?.click()

  const handleWmDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    setIsWmDragging(true)
  }

  const handleWmDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleWmDragLeave = () => {
    setIsWmDragging(false)
  }

  const handleWmDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsWmDragging(false)
    const f = e.dataTransfer.files?.[0] ?? null
    if (f && !f.type.startsWith('image/')) {
      setError('请拖拽图片文件')
      return
    }
    setWmImageFile(f)
    setWmImageFileId(null)
    setError('')
  }

  // ── Preview & Submit handlers ────────────────────────────────────────────
  const handlePreview = async () => {
    setError('')
    if (!pdfFile) return
    const p = paramsRef.current
    setPreviewLoading(true)
    try {
      // Upload PDF if not yet uploaded
      let pid = pdfFileId
      if (!pid) {
        const r = await uploadFile(pdfFile)
        pid = r.file_id
        setPdfFileId(pid)
      }

      // Upload watermark image if needed
      let wmId = p.wmImageFileId
      if (p.watermarkType === 'image' && wmImageFile && !wmId) {
        const r = await uploadFile(wmImageFile)
        wmId = r.file_id
        setWmImageFileId(wmId)
      }

      const params = buildParams()
      if (p.watermarkType === 'image' && wmId) {
        params.watermark_file_id = wmId
      }

      const res = await fetch('/api/previews/watermark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_id: pid,
          watermark_type: p.watermarkType,
          params,
          max_width: 200,
        }),
      })
      if (!res.ok) {
        const errText = await res.text()
        throw new Error(errText || 'Preview failed')
      }
      const data: PreviewResponse = await res.json()
      setPreviewUrl(data.preview_image_url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!pdfFile) return
    setError('')
    const p = paramsRef.current
    setUploading(true)
    try {
      // Upload PDF if not yet uploaded
      let pid = pdfFileId
      if (!pid) {
        const r = await uploadFile(pdfFile)
        pid = r.file_id
        setPdfFileId(pid)
      }

      let inputFileIds = [pid]

      // Upload watermark image if needed
      let wmId = p.wmImageFileId
      if (p.watermarkType === 'image' && wmImageFile && !wmId) {
        const r = await uploadFile(wmImageFile)
        wmId = r.file_id
        setWmImageFileId(wmId)
      }

      const params = buildParams()
      if (p.watermarkType === 'image' && wmId) {
        params.watermark_file_id = wmId
      }

      const created = await createTask('watermark_pdf', inputFileIds, params)
      setTask(created)

      pollRef.current = setInterval(async () => {
        const updated = await getTask(created.task_id)
        if (updated.status === 'succeeded' || updated.status === 'failed') {
          if (pollRef.current !== null) {
            clearInterval(pollRef.current)
            pollRef.current = null
          }
          setTask(updated)
        }
      }, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  // ── Sync state → ref on every render (ref always has latest values) ─────
  paramsRef.current = {
    watermarkType,
    text,
    fontSize,
    color,
    wmImageFileId,
    scale,
    opacity,
    rotation,
    position,
    tileMode,
    gridAxis,
    gridSpacing,
    tileSpacing,
    pageRange,
  }

  return (
    <section className="page">
      <h1>PDF 加水印</h1>
      <p className="text-muted">为 PDF 添加文字或图片水印，支持透明度、旋转、平铺等设置。</p>

      <div className="form-card form-card-wide">
        {/* Tab bar */}
        <div className="tab-bar">
          <button
            className={`tab-item${watermarkType === 'text' ? ' active' : ''}`}
            onClick={() => {
              setWatermarkType('text')
              setTileMode('full')
              setFontSize(32)
              setOpacity(0.25)
            }}
          >
            文字水印
          </button>
          <button
            className={`tab-item${watermarkType === 'image' ? ' active' : ''}`}
            onClick={() => {
              setWatermarkType('image')
              setTileMode('single')
              setOpacity(0.25)
            }}
          >
            图片水印
          </button>
        </div>

        {/* PDF file input — drag & drop */}
        <label className="form-label">选择 PDF 文件</label>
        <div
          className={`drop-zone${isPdfDragging ? ' dragging' : ''}${pdfFile ? ' has-file' : ''}`}
          onClick={handlePdfDropZoneClick}
          onDragEnter={handlePdfDragEnter}
          onDragOver={handlePdfDragOver}
          onDragLeave={handlePdfDragLeave}
          onDrop={handlePdfDrop}
        >
          <input
            ref={pdfFileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handlePdfFileChange}
            hidden
          />
          <Upload size={24} className="drop-zone-icon" />
          <span className="drop-zone-text">
            {pdfFile ? pdfFile.name : '点击或拖拽 PDF 文件到此处'}
          </span>
        </div>

        {/* Text watermark controls */}
        {watermarkType === 'text' && (
          <>
            <label className="form-label">水印文字</label>
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="输入水印文字"
            />

            <div className="slider-row">
              <label className="form-label">字号</label>
              <input
                type="range"
                min={tileMode === 'dense' ? 4 : 8}
                max={tileMode === 'dense' ? 12 : 120}
                step={1}
                value={fontSize}
                onChange={(e) => setFontSize(Number(e.target.value))}
              />
              <span className="slider-value">{fontSize}px</span>
            </div>

            <div className="slider-row">
              <label className="form-label">颜色</label>
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
              />
              <span className="slider-value">{color}</span>
            </div>
          </>
        )}

        {/* Image watermark controls */}
        {watermarkType === 'image' && (
          <>
            <label className="form-label">选择水印图片</label>
            <div
              className={`drop-zone${isWmDragging ? ' dragging' : ''}${wmImageFile ? ' has-file' : ''}`}
              onClick={handleWmDropZoneClick}
              onDragEnter={handleWmDragEnter}
              onDragOver={handleWmDragOver}
              onDragLeave={handleWmDragLeave}
              onDrop={handleWmDrop}
            >
              <input
                ref={wmFileInputRef}
                type="file"
                accept="image/*"
                onChange={(e) => {
                  setWmImageFile(e.target.files?.[0] ?? null)
                  setWmImageFileId(null)
                }}
                hidden
              />
              <Upload size={24} className="drop-zone-icon" />
              <span className="drop-zone-text">
                {wmImageFile ? wmImageFile.name : '点击或拖拽图片文件到此处'}
              </span>
            </div>

            <div className="slider-row">
              <label className="form-label">缩放</label>
              <input
                type="range"
                min={0.1}
                max={3.0}
                step={0.05}
                value={scale}
                onChange={(e) => setScale(Number(e.target.value))}
              />
              <span className="slider-value">{scale.toFixed(2)}x</span>
            </div>
          </>
        )}

        {/* Common controls */}
        <div className="slider-row">
          <label className="form-label">{tileMode === 'dense' ? '不透明度' : '透明度'}</label>
          <input
            type="range"
            min={tileMode === 'dense' ? 0.02 : 0}
            max={tileMode === 'dense' ? 0.15 : 1}
            step={tileMode === 'dense' ? 0.01 : 0.05}
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
          />
          <span className="slider-value">{(opacity * 100).toFixed(tileMode === 'dense' ? 0 : 0)}%</span>
        </div>

        {tileMode !== 'dense' && (
          <div className="slider-row">
            <label className="form-label">旋转</label>
            <input
              type="range"
              min={-90}
              max={90}
              step={1}
              value={rotation}
              onChange={(e) => setRotation(Number(e.target.value))}
            />
            <span className="slider-value">{rotation}°</span>
          </div>
        )}

        {tileMode === 'single' && (
          <div className="slider-row">
            <label className="form-label">位置</label>
            <select value={position} onChange={(e) => setPosition(e.target.value)}>
              {POSITIONS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        )}

        {tileMode === 'full' && (
          <div className="slider-row">
            <label className="form-label">密度</label>
            <input
              type="range"
              min={0.8}
              max={4.0}
              step={0.1}
              value={tileSpacing}
              onChange={(e) => setTileSpacing(Number(e.target.value))}
            />
            <span className="slider-value">{tileSpacing.toFixed(1)}x</span>
          </div>
        )}

        {tileMode === 'grid' && (
          <>
            <div className="slider-row">
              <label className="form-label">方向</label>
              <select value={gridAxis} onChange={(e) => setGridAxis(e.target.value as 'x' | 'y')}>
                <option value="x">水平 (x轴)</option>
                <option value="y">垂直 (y轴)</option>
              </select>
            </div>
            <div className="slider-row">
              <label className="form-label">间距</label>
              <input
                type="range"
                min={1.0}
                max={5.0}
                step={0.1}
                value={gridSpacing}
                onChange={(e) => setGridSpacing(Number(e.target.value))}
              />
              <span className="slider-value">{gridSpacing.toFixed(1)}x</span>
            </div>
          </>
        )}

        <div className="slider-row">
          <label className="form-label">平铺模式</label>
          <select value={tileMode} onChange={(e) => {
            const newMode = e.target.value
            setTileMode(newMode)
            if (newMode === 'dense') {
              setFontSize(6)
              setOpacity(0.08)
              setRotation(0)
            } else if (newMode === 'grid') {
              setGridAxis('x')
              setGridSpacing(2.0)
            } else {
              setFontSize(32)
              setOpacity(0.25)
              setRotation(-30)
            }
          }}>
            {(watermarkType === 'text' ? TEXT_TILE_MODES : IMAGE_TILE_MODES).map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        <div className="slider-row">
          <label className="form-label">页码范围</label>
          <input
            value={pageRange}
            onChange={(e) => setPageRange(e.target.value)}
            placeholder="all"
          />
        </div>

        {/* Actions */}
        <div className="form-actions">
          <button
            className="btn btn-secondary"
            disabled={!pdfFile || previewLoading}
            onClick={handlePreview}
          >
            <Eye size={16} style={{ marginRight: 6 }} />
            {previewLoading ? '生成中...' : '预览'}
          </button>
          <button
            className="btn"
            disabled={!pdfFile || uploading}
            onClick={handleSubmit}
          >
            <Upload size={16} style={{ marginRight: 6 }} />
            {uploading ? '处理中...' : '开始加水印'}
          </button>
        </div>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {/* Preview */}
      {previewUrl && (
        <div className="preview-container">
          <h3 className="preview-title">预览效果（第一页）</h3>
          <img src={previewUrl} alt="Watermark preview" />
        </div>
      )}

      {/* Result */}
      {task && (
        <div className="result-card">
          <p><strong>状态：</strong>{task.status === 'succeeded' ? '✅ 成功' : task.status === 'failed' ? '❌ 失败' : task.status}</p>
          {task.warnings && task.warnings.length > 0 && (
            <div className="warning-msg">
              {task.warnings.map((w, i) => <p key={i}>{w}</p>)}
            </div>
          )}
          {task.error_message && (
            <p className="error-msg">错误：{task.error_message}</p>
          )}
          {task.status === 'succeeded' && task.output_files.length > 0 && (
            <a
              href={`/api/files/${task.output_files[0].file_id}/download`}
              className="btn"
              download
            >
              <Download size={16} style={{ marginRight: 6 }} />
              下载水印 PDF
            </a>
          )}
        </div>
      )}
    </section>
  )
}
