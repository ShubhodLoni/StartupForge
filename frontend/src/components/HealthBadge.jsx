import { useEffect, useState } from 'react'

import { getHealth } from '../api/client'

const DOT = {
  ok: 'bg-green-500',
  warn: 'bg-yellow-500',
  down: 'bg-red-500',
  loading: 'bg-neutral-600',
}

function Badge({ kind, children, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border border-line px-2.5 py-1 text-xs text-neutral-400 ${className}`}
    >
      <span className={`size-1.5 rounded-full ${DOT[kind]}`} />
      {children}
    </span>
  )
}

export default function HealthBadge() {
  const [state, setState] = useState({ kind: 'loading', label: 'Checking…' })
  const [searchOff, setSearchOff] = useState(false)

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((h) => {
        if (cancelled) return
        setSearchOff(h.llm_configured && !h.search_configured)
        setState(
          h.llm_configured
            ? { kind: 'ok', label: h.model }
            : { kind: 'warn', label: 'GROQ_API_KEY missing' },
        )
      })
      .catch(() => !cancelled && setState({ kind: 'down', label: 'Backend offline' }))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <span className="flex items-center gap-2">
      {searchOff && (
        <Badge kind="warn" className="hidden sm:inline-flex">
          Web search off
        </Badge>
      )}
      <Badge kind={state.kind}>{state.label}</Badge>
    </span>
  )
}
