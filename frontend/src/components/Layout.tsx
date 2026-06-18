import { Link, Outlet, useLocation } from 'react-router-dom'
import {
  FileImage,
  FileArchive,
  Scissors,
  Trash2,
  History,
  Home,
  FileWarning,
  FileText,
  Shield,
  Search,
  Settings,
} from 'lucide-react'

export const navItems = [
  { to: '/', label: '首页', icon: Home },
  { to: '/pdf-to-png', label: 'PDF 转 PNG', icon: FileImage },
  { to: '/images-to-pdf', label: '图片转 PDF', icon: FileArchive },
  { to: '/split-pdf', label: 'PDF 拆分', icon: Scissors },
  { to: '/watermark', label: 'PDF 加水印', icon: FileWarning },
  { to: '/remove-pages', label: '删除指定页', icon: Trash2 },
  { to: '/pdf-to-word', label: 'PDF 转 Word', icon: FileText },
  { to: '/protect-pdf', label: '版权保护', icon: Shield },
  { to: '/trace-query', label: '溯源查询', icon: Search },
  { to: '/history', label: '历史任务', icon: History },
]

export default function Layout() {
  const { pathname } = useLocation()

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>PDF 工具箱</h2>
        </div>
        <nav>
          {navItems.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-link${pathname === to ? ' active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <main className="main-content">
        <header className="main-content-header">
          <Link to="/settings" className="settings-btn" title="设置">
            <Settings size={18} />
          </Link>
        </header>
        <div className="main-content-body">
          <Outlet />
        </div>
        <footer className="app-footer">
          <p>© {new Date().getFullYear()} <a href="https://github.com/z242235718/pdf-tools" target="_blank" rel="noopener noreferrer">w2422</a> · 保留所有权利</p>
        </footer>
      </main>
    </div>
  )
}
