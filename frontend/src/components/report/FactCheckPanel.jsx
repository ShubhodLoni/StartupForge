import { AlertTriangle, CheckCircle2, Circle, XCircle } from 'lucide-react'

import { useCitations } from './citations'
import { EmptyState, Section } from './ui'

const VERDICTS = {
  unsupported: { label: 'Citation removed', icon: XCircle, className: 'text-red-400' },
  partial: { label: 'Partly supported', icon: AlertTriangle, className: 'text-yellow-400' },
  supported: { label: 'Supported', icon: CheckCircle2, className: 'text-green-500' },
  unchecked: { label: 'Not checked', icon: Circle, className: 'text-neutral-600' },
}
const ORDER = ['unsupported', 'partial', 'supported', 'unchecked']

const ISSUES = {
  not_in_cited_source: 'Figure not found in the cited source',
  uncited: 'Figure has no source',
  not_in_financial_model: 'Figure not in the computed financial model',
}

function humanize(location) {
  return location
    .replace(/\[(\d+)\]/g, (_, i) => ` #${Number(i) + 1}`)
    .replace(/[._]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-2 text-2xl font-medium tracking-tight text-white">{value}</p>
    </div>
  )
}

function SourceLink({ id }) {
  const { ids, openSource } = useCitations()
  if (!ids.has(id)) return <span className="font-mono text-[11px] text-neutral-600">Source {id}</span>
  return (
    <a
      href={`#source-${id}`}
      onClick={(e) => {
        if (!openSource) return
        e.preventDefault()
        openSource(id)
      }}
      className="font-mono text-[11px] text-neutral-400 underline decoration-neutral-700 underline-offset-2 hover:text-white"
    >
      Source {id}
    </a>
  )
}

export default function FactCheckPanel({ factCheck }) {
  if (!factCheck) return <EmptyState>Not available for this report. Run a new analysis to generate it.</EmptyState>

  const count = (v) => factCheck.items.filter((i) => i.verdict === v).length
  const items = [...factCheck.items].sort((a, b) => ORDER.indexOf(a.verdict) - ORDER.indexOf(b.verdict))

  return (
    <div className="space-y-4">
      <p className="text-sm leading-relaxed text-neutral-500">
        The critic agent compared each cited claim with the exact passage it cites. Citations it judged unsupported
        were removed from the report. Separately, every statistic-like figure ($, %, millions) was checked in code
        against its cited source.
      </p>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Claims checked" value={factCheck.claims_checked} />
        <Stat label="Supported" value={count('supported')} />
        <Stat label="Partly supported" value={count('partial')} />
        <Stat label="Citations removed" value={factCheck.removed_citations} />
        <Stat label="Figures flagged" value={factCheck.figure_flags.length} />
      </div>

      {factCheck.figure_flags.length > 0 && (
        <Section title="Figures to verify">
          <ul className="divide-y divide-line">
            {factCheck.figure_flags.map((f, i) => (
              <li key={i} className="flex gap-3 py-3 text-sm first:pt-0 last:pb-0">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-yellow-400" aria-hidden />
                <div className="min-w-0 space-y-1">
                  <p className="text-neutral-200">
                    <span className="font-mono text-white">{f.figure}</span>{' '}
                    <span className="text-neutral-500">· {ISSUES[f.issue]}</span>
                  </p>
                  <p className="text-neutral-400">“{f.text}”</p>
                  <p className="text-xs text-neutral-600">{humanize(f.location)}</p>
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Claim review">
        {items.length ? (
          <ul className="divide-y divide-line">
            {items.map((item, i) => {
              const v = VERDICTS[item.verdict]
              const Icon = v.icon
              return (
                <li key={i} className="grid gap-2 py-4 text-sm first:pt-0 last:pb-0 sm:grid-cols-[11rem_1fr]">
                  <p className="flex items-center gap-2 text-neutral-300">
                    <Icon className={`size-4 shrink-0 ${v.className}`} aria-hidden />
                    {v.label}
                  </p>
                  <div className="min-w-0 space-y-1">
                    <p className="leading-relaxed text-neutral-200">{item.claim}</p>
                    {item.reason && <p className="leading-relaxed text-neutral-500">{item.reason}</p>}
                    <p className="flex flex-wrap items-center gap-2 text-xs text-neutral-600">
                      <SourceLink id={item.source_id} />
                      <span>·</span>
                      <span>{humanize(item.location)}</span>
                    </p>
                  </div>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="text-sm text-neutral-500">No cited claims to check.</p>
        )}
      </Section>
    </div>
  )
}
