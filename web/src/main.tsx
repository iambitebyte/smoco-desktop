import React, { lazy, Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import './i18n'
import './styles/globals.css'

// 路由级 chunk 拆分
const Home = lazy(() => import('./pages/Home'))
const Download = lazy(() => import('./pages/Download'))
const Docs = lazy(() => import('./pages/Docs'))
const Changelog = lazy(() => import('./pages/Changelog'))

function PageFallback() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-edge border-t-brand-400 animate-spin" />
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route element={<App />}>
            <Route index element={<Home />} />
            <Route path="download" element={<Download />} />
            <Route path="docs" element={<Docs />} />
            <Route path="changelog" element={<Changelog />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  </React.StrictMode>,
)
