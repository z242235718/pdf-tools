import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, FileImage, FileArchive, Scissors, Trash2, History, FileWarning, Shield, Search } from 'lucide-react'
import { navItems } from '../components/Layout'

const toolInfo: Record<string, { desc: string; icon: typeof FileText }> = {
  '/pdf-to-png':    { desc: '将 PDF 文件按页渲染为 PNG 图片', icon: FileImage },
  '/images-to-pdf': { desc: '将多张图片合并为一个 PDF 文件', icon: FileArchive },
  '/split-pdf':     { desc: '按页码拆分 PDF 文件为多个文档', icon: Scissors },
  '/watermark':     { desc: '为 PDF 添加文字或图片水印', icon: FileWarning },
  '/remove-pages':  { desc: '删除 PDF 中的指定页面', icon: Trash2 },
  '/pdf-to-word':   { desc: '将 PDF 文件转换为 Word 文档', icon: FileText },
  '/protect-pdf':   { desc: '为 PDF 添加可追踪的版权指纹', icon: Shield },
  '/trace-query':   { desc: '查询 PDF 指纹溯源信息', icon: Search },
  '/history':       { desc: '查看历史任务记录与下载结果', icon: History },
}

export default function HomePage() {
  const navigate = useNavigate()
  const [healthOk, setHealthOk] = useState<boolean | null>(null)
  const [healthTime, setHealthTime] = useState('')

  const fmtTime = () => {
    const d = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/health')
        if (!res.ok) throw new Error(res.statusText)
        await res.json()
        setHealthOk(true)
      } catch {
        setHealthOk(false)
      }
      setHealthTime(fmtTime())
    }

    check()
    const id = setInterval(check, 15_000)
    return () => clearInterval(id)
  }, [])

  return (
    <section className="page">
      {/* Hero */}
      <div className="hero-card">
        <FileText size={36} className="hero-icon" />
        <h1>Web PDF 工具箱</h1>
        <p>
          快速进行 PDF 转换、拆分、编辑等操作。
          支持 PDF 转 PNG、图片合成 PDF、
          按页拆分、删除指定页面等功能，全部在浏览器端完成。
        </p>
      </div>

      {/* Tool quick-access cards */}
      <div className="tool-grid">
        {navItems
          .filter((item) => item.to !== '/')
          .map(({ to, label, icon: Icon }) => {
            const info = toolInfo[to]
            return (
              <div key={to} className="tool-card" onClick={() => navigate(to)}>
                <div className="tool-card-icon">
                  <Icon size={32} />
                </div>
                <h3>{label}</h3>
                <p>{info?.desc ?? ''}</p>
              </div>
            )
          })}
      </div>

      {/* System status */}
      <div className="status-bar">
        <div className="status-bar-left">
          <span className={`status-dot${healthOk === true ? ' ok' : ''}${healthOk === false ? ' err' : ''}`} />
          <span className="status-text">
            {healthOk === null
              ? '检查中...'
              : healthOk
                ? '后端运行正常'
                : '后端异常'}
          </span>
          <span className="status-version">· v0.1 MVP</span>
        </div>
        {healthTime && <span className="status-time">{healthTime}</span>}
      </div>
    </section>
  )
}
