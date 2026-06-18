import { useState, useEffect } from 'react'
import { Save, AlertTriangle, Type, Menu } from 'lucide-react'
import { getSettings, updateSettings, clearTasks } from '../api/client'

export default function SettingsPage() {
  const [domainUrl, setDomainUrl] = useState('')
  const [passwordLength, setPasswordLength] = useState(8)
  const [qrCodeVisible, setQrCodeVisible] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [showClearModal, setShowClearModal] = useState(false)
  const [clearConfirmText, setClearConfirmText] = useState('')
  const [clearing, setClearing] = useState(false)
  const [clearMessage, setClearMessage] = useState('')

  const [fontSize, setFontSize] = useState(() => {
    return parseInt(localStorage.getItem('ui_font_size') || '14')
  })

  const [sidebarFontSize, setSidebarFontSize] = useState(() => {
    return parseInt(localStorage.getItem('sidebar_font_size') || '14')
  })

  useEffect(() => {
    getSettings()
      .then((data) => {
        setDomainUrl(data.domain_url)
        setPasswordLength(data.password_length)
        setQrCodeVisible(data.qr_code_visible)
      })
      .catch(() => setMessage('加载设置失败'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    try {
      await updateSettings({ domain_url: domainUrl, password_length: passwordLength, qr_code_visible: qrCodeVisible })
      setMessage('✅ 设置已保存')
    } catch (err) {
      setMessage(err instanceof Error ? `❌ ${err.message}` : '❌ 保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleClearConfirm = async () => {
    setClearing(true)
    setClearMessage('')
    try {
      await clearTasks()
      setClearMessage('✅ 历史记录已清空')
      setShowClearModal(false)
      setClearConfirmText('')
    } catch (err) {
      setClearMessage(err instanceof Error ? `❌ ${err.message}` : '❌ 清空失败')
    } finally {
      setClearing(false)
    }
  }

  return (
    <section className="page">
      <h1>设置</h1>
      <p className="text-muted">
        配置系统全局参数，影响版权保护、二维码生成等功能行为。
      </p>

      <div className="form-card">
        <label className="form-label">域名</label>
        <input
          type="text"
          value={domainUrl}
          onChange={(e) => setDomainUrl(e.target.value)}
          placeholder="例如：https://example.com"
          disabled={loading}
        />
        <p className="text-muted" style={{ fontSize: 13, marginTop: 0 }}>
          留空则二维码只编码指纹 ID，扫码后不会跳转。
        </p>

        <label className="form-label">生成随机密码长度</label>
        <input
          type="number"
          min={4}
          max={32}
          value={passwordLength}
          onChange={(e) => setPasswordLength(Number(e.target.value))}
          disabled={loading}
        />
        <p className="text-muted" style={{ fontSize: 13, marginTop: 0 }}>
          版权保护开启密码保护时，自动生成随机密码的字符长度（4-32）。
        </p>

        <div className="checkbox-row">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={qrCodeVisible}
              onChange={(e) => setQrCodeVisible(e.target.checked)}
              disabled={loading}
            />
            版权保护二维码是否可见
          </label>
        </div>
        <p className="text-muted" style={{ fontSize: 13, marginTop: 0 }}>
          关闭后，版权保护将不生成二维码，仅保留页脚水印文字和元数据指纹。
        </p>

        <button
          className="btn"
          onClick={handleSave}
          disabled={loading || saving}
        >
          <Save size={16} style={{ marginRight: 6 }} />
          {saving ? '保存中...' : '保存'}
        </button>

        {message && <p className="text-muted" style={{ marginTop: 8 }}>{message}</p>}
      </div>

      {/* ── Font size ── */}
      <div className="form-card" style={{ marginTop: '1rem' }}>
        <label className="form-label">
          <Type size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          界面字体大小
        </label>
        <div className="font-size-control">
          <input
            type="range"
            min={12}
            max={20}
            step={1}
            value={fontSize}
            onChange={(e) => {
              const v = Number(e.target.value)
              setFontSize(v)
              localStorage.setItem('ui_font_size', String(v))
              document.documentElement.style.setProperty('--font-size', v + 'px')
            }}
          />
          <span className="font-size-value">{fontSize}px</span>
        </div>
        <p className="text-muted" style={{ fontSize: 13, marginTop: 0 }}>
          调整左侧菜单栏和主界面内容的字体大小（12px – 20px），实时生效。
        </p>
      </div>

      {/* ── Sidebar font size ── */}
      <div className="form-card" style={{ marginTop: '1rem' }}>
        <label className="form-label">
          <Menu size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          菜单栏字体大小
        </label>
        <div className="font-size-control">
          <input
            type="range"
            min={12}
            max={20}
            step={1}
            value={sidebarFontSize}
            onChange={(e) => {
              const v = Number(e.target.value)
              setSidebarFontSize(v)
              localStorage.setItem('sidebar_font_size', String(v))
              document.documentElement.style.setProperty('--sidebar-font-size', v + 'px')
            }}
          />
          <span className="font-size-value">{sidebarFontSize}px</span>
        </div>
        <p className="text-muted" style={{ fontSize: 13, marginTop: 0 }}>
          单独调整左侧菜单栏的字体大小（12px – 20px），实时生效。
        </p>
      </div>

      {/* ── Clear history ── */}
      <div className="form-card" style={{ marginTop: '1rem' }}>
        <details>
          <summary style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--text-strong)' }}>
            清空历史记录
          </summary>
          <p className="text-muted" style={{ marginTop: '0.75rem' }}>
            清空所有最近处理的任务列表。此操作不可恢复。
          </p>
          <button
            className="btn-danger"
            onClick={() => setShowClearModal(true)}
            type="button"
          >
            <AlertTriangle size={16} style={{ marginRight: 6 }} />
            清空历史记录
          </button>
          {clearMessage && <p className="text-muted" style={{ marginTop: 8 }}>{clearMessage}</p>}
        </details>
      </div>

      {/* ── Clear confirmation modal ── */}
      {showClearModal && (
        <div className="modal-overlay" onClick={() => { if (!clearing) setShowClearModal(false) }}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>清空历史记录</h3>
            <p>注意：此操作会清空所有最近处理的任务列表，且日后无法找回。请考虑好后在操作</p>
            <input
              type="text"
              value={clearConfirmText}
              onChange={(e) => setClearConfirmText(e.target.value)}
              placeholder="请输入：我确认要清空历史记录"
              disabled={clearing}
            />
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => { setShowClearModal(false); setClearConfirmText('') }}
                disabled={clearing}
                type="button"
              >
                取消
              </button>
              <button
                className="btn-danger"
                disabled={clearConfirmText !== '我确认要清空历史记录' || clearing}
                onClick={handleClearConfirm}
                type="button"
              >
                {clearing ? '清空中...' : '确认清空'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
