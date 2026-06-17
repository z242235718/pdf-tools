import { useState, useEffect } from 'react'
import { Save } from 'lucide-react'
import { getSettings, updateSettings } from '../api/client'

export default function SettingsPage() {
  const [domainUrl, setDomainUrl] = useState('')
  const [passwordLength, setPasswordLength] = useState(8)
  const [qrCodeVisible, setQrCodeVisible] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

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
    </section>
  )
}
