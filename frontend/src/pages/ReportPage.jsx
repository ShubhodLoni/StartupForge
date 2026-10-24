import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getReport, recomputeFinance, updateReportFinance } from '../api/client'
import ReportView from '../components/ReportView'
import { loadReport, saveReport } from '../lib/reportStore'

export default function ReportPage() {
  const { id } = useParams()
  const [state, setState] = useState({ id: null, status: 'loading', data: null, origin: null })

  useEffect(() => {
    let cancelled = false
    getReport(id)
      .then((data) => {
        if (cancelled) return
        saveReport(data)
        setState({ id, status: 'ready', data, origin: 'server' })
      })
      .catch(() => {
        if (cancelled) return
        const local = loadReport(id)
        setState(local ? { id, status: 'ready', data: local, origin: 'local' } : { id, status: 'missing', data: null })
      })
    return () => {
      cancelled = true
    }
  }, [id])

  async function recalculateFinance(assumptions) {
    const current = state.data.finance
    const finance =
      state.origin === 'server'
        ? await updateReportFinance(id, assumptions)
        : {
            ...(await recomputeFinance(assumptions)),
            rationale: current.rationale,
            adjustments: [],
            original_assumptions: current.original_assumptions || current.assumptions,
          }
    const data = { ...state.data, finance }
    saveReport(data)
    setState((s) => ({ ...s, data }))
  }

  const loading = state.status === 'loading' || state.id !== id

  return (
    <div className="space-y-8">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-white">
        <ArrowLeft className="size-4" /> New analysis
      </Link>
      {loading ? (
        <p className="text-sm text-neutral-600">Loading report…</p>
      ) : state.data ? (
        <ReportView key={id} data={state.data} onRecalculateFinance={recalculateFinance} />
      ) : (
        <div className="rounded-xl border border-line bg-panel p-8 text-center">
          <p className="text-neutral-300">Report not found.</p>
          <p className="mt-1 text-sm text-neutral-500">It may have been created on another server or deleted.</p>
        </div>
      )}
    </div>
  )
}
