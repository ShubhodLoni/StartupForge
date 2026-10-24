import { motion } from 'framer-motion'
import { AlertCircle, Clock } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { listReports as listServerReports, streamReport } from '../api/client'
import AgentProgress from '../components/AgentProgress'
import IdeaForm from '../components/IdeaForm'
import { summarizeAgentOutput } from '../lib/agents'
import { listReports as listLocalReports, saveReport } from '../lib/reportStore'

export default function NewReportPage() {
  const navigate = useNavigate()
  const [running, setRunning] = useState(false)
  const [statuses, setStatuses] = useState({})
  const [details, setDetails] = useState({})
  const [error, setError] = useState(null)
  const abortRef = useRef(null)
  const [recent, setRecent] = useState(() => listLocalReports().slice(0, 5))

  useEffect(() => {
    let cancelled = false
    listServerReports(5)
      .then((reports) => !cancelled && reports.length && setRecent(reports))
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => () => abortRef.current?.abort(), [])

  async function handleSubmit(payload) {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setRunning(true)
    setError(null)
    setStatuses({})
    setDetails({})
    let finished = false

    try {
      await streamReport(payload, {
        signal: controller.signal,
        onEvent: ({ event, data }) => {
          if (event === 'agent_started') setStatuses((s) => ({ ...s, [data.agent]: 'running' }))
          else if (event === 'agent_completed') {
            setStatuses((s) => ({ ...s, [data.agent]: 'done' }))
            const summary = summarizeAgentOutput(data.agent, data.output)
            if (summary) setDetails((d) => ({ ...d, [data.agent]: summary }))
          }
          else if (event === 'error') {
            finished = true
            setStatuses((s) =>
              Object.fromEntries(Object.entries(s).map(([k, v]) => [k, v === 'running' ? 'error' : v])),
            )
            setError(data.detail || 'The agent pipeline failed.')
          } else if (event === 'complete') {
            finished = true
            saveReport(data)
            navigate(`/reports/${data.id}`)
          }
        },
      })
      if (!finished) setError('The connection closed before the report was finished.')
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'Could not reach the backend.')
    } finally {
      if (!controller.signal.aborted) setRunning(false)
    }
  }

  const started = running || Object.keys(statuses).length > 0

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
      <div className="space-y-8">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
          <h1 className="text-4xl font-semibold tracking-tighter text-white sm:text-5xl">
            Turn an idea into a startup brief.
          </h1>
          <p className="max-w-2xl text-neutral-400">
            Specialized AI agents research your market and write a structured brief, and they mark every claim that
            still needs checking against real data.
          </p>
        </motion.div>

        <div className="rounded-xl border border-line bg-panel p-5 sm:p-6">
          <IdeaForm onSubmit={handleSubmit} disabled={running} />
        </div>

        {error && (
          <div role="alert" className="flex gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <p className="break-words">{error}</p>
          </div>
        )}
      </div>

      <aside className="space-y-6">
        <div className="rounded-xl border border-line bg-panel p-5">
          <h2 className="mb-4 text-xs font-medium uppercase tracking-widest text-neutral-500">Agent pipeline</h2>
          <AgentProgress statuses={statuses} details={details} />
          {!started && <p className="mt-4 text-xs text-neutral-500">Agents run in sequence. Each one builds on the last.</p>}
        </div>

        {recent.length > 0 && (
          <div className="rounded-xl border border-line bg-panel p-5">
            <h2 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-neutral-500">
              <Clock className="size-4" /> Recent
            </h2>
            <ul className="space-y-1">
              {recent.map((r) => (
                <li key={r.id}>
                  <Link
                    to={`/reports/${r.id}`}
                    className="block truncate rounded-md px-2 py-1.5 text-sm text-neutral-300 hover:bg-white/5 hover:text-white"
                  >
                    {r.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  )
}
