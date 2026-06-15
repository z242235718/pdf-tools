import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import PdfToPngPage from './pages/PdfToPngPage'
import ImagesToPdfPage from './pages/ImagesToPdfPage'
import SplitPdfPage from './pages/SplitPdfPage'
import RemovePdfPagesPage from './pages/RemovePdfPagesPage'
import TaskDetailPage from './pages/TaskDetailPage'
import HistoryPage from './pages/HistoryPage'
import './App.css'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/pdf-to-png" element={<PdfToPngPage />} />
        <Route path="/images-to-pdf" element={<ImagesToPdfPage />} />
        <Route path="/split-pdf" element={<SplitPdfPage />} />
        <Route path="/remove-pages" element={<RemovePdfPagesPage />} />
        <Route path="/task/:taskId" element={<TaskDetailPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
    </Routes>
  )
}
