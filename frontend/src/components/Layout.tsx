import { Link, Outlet, useLocation } from 'react-router-dom'
import {
  FileImage,
  FileArchive,
  Scissors,
  Trash2,
  History,
  Home,
} from 'lucide-react'

export const navItems = [
  { to: '/', label: '首页', icon: Home },
  { to: '/pdf-to-png', label: 'PDF 转 PNG', icon: FileImage },
  { to: '/images-to-pdf', label: '图片转 PDF', icon: FileArchive },
  { to: '/split-pdf', label: 'PDF 拆分', icon: Scissors },
  { to: '/remove-pages', label: '删除指定页', icon: Trash2 },
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
        <Outlet />
      </main>
    </div>
  )
}
