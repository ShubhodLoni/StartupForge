import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import NewReportPage from './pages/NewReportPage'

const ReportPage = lazy(() => import('./pages/ReportPage'))

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<NewReportPage />} />
          <Route
            path="reports/:id"
            element={
              <Suspense fallback={<p className="text-sm text-neutral-600">Loading report…</p>}>
                <ReportPage />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
