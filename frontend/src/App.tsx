import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import PdfToPngPage from './pages/PdfToPngPage'
import ImagesToPdfPage from './pages/ImagesToPdfPage'
import SplitPdfPage from './pages/SplitPdfPage'
import WatermarkPdfPage from './pages/WatermarkPdfPage'
import RemovePdfPagesPage from './pages/RemovePdfPagesPage'
import PdfToWordPage from './pages/PdfToWordPage'
import ProtectPdfPage from './pages/ProtectPdfPage'
import SettingsPage from './pages/SettingsPage'
import TraceQueryPage from './pages/TraceQueryPage'
import TaskDetailPage from './pages/TaskDetailPage'
import HistoryPage from './pages/HistoryPage'
import './App.css'

export default function App() {
  // Restore saved font size from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('ui_font_size')
    if (saved) {
      document.documentElement.style.setProperty('--font-size', saved + 'px')
    }
    const savedSidebar = localStorage.getItem('sidebar_font_size')
    if (savedSidebar) {
      document.documentElement.style.setProperty('--sidebar-font-size', savedSidebar + 'px')
    }
  }, [])

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/pdf-to-png" element={<PdfToPngPage />} />
        <Route path="/images-to-pdf" element={<ImagesToPdfPage />} />
        <Route path="/split-pdf" element={<SplitPdfPage />} />
        <Route path="/watermark" element={<WatermarkPdfPage />} />
        <Route path="/remove-pages" element={<RemovePdfPagesPage />} />
        <Route path="/pdf-to-word" element={<PdfToWordPage />} />
        <Route path="/protect-pdf" element={<ProtectPdfPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/trace-query" element={<TraceQueryPage />} />
        <Route path="/task/:taskId" element={<TaskDetailPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
    </Routes>
  )
}
