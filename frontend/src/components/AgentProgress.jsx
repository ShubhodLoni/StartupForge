import { motion } from 'framer-motion'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

import { AGENTS } from '../lib/agents'

const STATUS = {
  idle: { icon: Circle, className: 'text-neutral-700', label: 'Waiting' },
  running: { icon: Loader2, className: 'text-white animate-spin', label: 'Running' },
  done: { icon: CheckCircle2, className: 'text-white', label: 'Done' },
  error: { icon: XCircle, className: 'text-red-400', label: 'Failed' },
}

export default function AgentProgress({ statuses, details = {} }) {
  return (
    <ol className="space-y-2">
      {AGENTS.map((agent, i) => {
        const status = statuses[agent.id] || 'idle'
        const { icon: StatusIcon, className, label } = STATUS[status]
        const AgentIcon = agent.icon
        return (
          <motion.li
            key={agent.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className={`flex items-start gap-3 rounded-lg border p-3 transition ${
              status === 'running' ? 'border-neutral-500 bg-white/[0.03]' : 'border-line'
            } ${status === 'idle' ? 'opacity-60' : ''}`}
          >
            <span className="grid size-8 shrink-0 place-items-center rounded-md border border-line">
              <AgentIcon className="size-3.5 text-neutral-300" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-white">{agent.name}</p>
              <p className={`text-xs leading-snug ${details[agent.id] ? 'text-neutral-300' : 'text-neutral-500'}`}>
                {details[agent.id] || agent.description}
              </p>
            </div>
            <span className="flex items-center gap-1.5 pt-1.5 text-xs text-neutral-500" aria-label={`${agent.name}: ${label}`}>
              <StatusIcon className={`size-4 ${className}`} />
              <span className="hidden sm:inline">{label}</span>
            </span>
          </motion.li>
        )
      })}
    </ol>
  )
}
