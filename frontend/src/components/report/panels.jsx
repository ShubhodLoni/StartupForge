import CitedText from '../CitedText'
import { useCitations } from './citations'
import { BulletList, EmptyState, Grid, Prose, Section } from './ui'

const MISSING = <EmptyState>Not available for this report. Run a new analysis to generate it.</EmptyState>

function FactCheckNotice({ factCheck, onOpen }) {
  if (!factCheck) return null
  const flagged = factCheck.figure_flags.length
  const parts = [
    `${factCheck.claims_checked} cited ${factCheck.claims_checked === 1 ? 'claim' : 'claims'} checked`,
    factCheck.removed_citations > 0 && `${factCheck.removed_citations} unsupported ${factCheck.removed_citations === 1 ? 'citation' : 'citations'} removed`,
    flagged > 0 && `${flagged} ${flagged === 1 ? 'figure' : 'figures'} to verify`,
  ].filter(Boolean)
  return (
    <button
      onClick={onOpen}
      className="flex w-full items-center justify-between gap-4 rounded-xl border border-line px-5 py-3 text-left text-sm text-neutral-400 transition hover:border-neutral-600 hover:text-white"
    >
      <span>Fact check: {parts.join(' · ')}</span>
      <span aria-hidden>→</span>
    </button>
  )
}

export function OverviewPanel({ report, factCheck, onOpenFactCheck }) {
  return (
    <div className="space-y-4">
      <FactCheckNotice factCheck={factCheck} onOpen={onOpenFactCheck} />
      <Section title="Executive summary">
        <Prose text={report.executive_summary} />
      </Section>
      <Grid>
        <Section title="Problem">
          <Prose text={report.problem} />
        </Section>
        <Section title="Solution">
          <Prose text={report.solution} />
        </Section>
      </Grid>
      <Section title="Value proposition">
        <Prose text={report.value_proposition} />
      </Section>
      {report.financial_summary && (
        <Section title="Financial outlook">
          <Prose text={report.financial_summary} />
        </Section>
      )}
      <Grid>
        <Section title="Target customers">
          <BulletList items={report.target_customers} />
        </Section>
        <Section title="Go-to-market">
          <BulletList items={report.go_to_market} ordered />
        </Section>
        <Section title="Risks">
          <BulletList items={report.risks} />
        </Section>
        <Section title="Next steps">
          <BulletList items={report.next_steps} ordered />
        </Section>
      </Grid>
      <Section title="Verify before relying on this" className="border-yellow-500/20">
        <BulletList items={report.verification_needed} />
      </Section>
    </div>
  )
}

export function MarketPanel({ research }) {
  if (!research) return MISSING
  return (
    <div className="space-y-4">
      <Section title="Market summary">
        <Prose text={research.market_summary} />
      </Section>
      <Grid>
        <Section title="Customer segments">
          <BulletList items={research.target_customers} />
        </Section>
        <Section title="Pain points">
          <BulletList items={research.pain_points} />
        </Section>
        <Section title="Trends">
          <BulletList items={research.key_trends} />
        </Section>
        <Section title="Risks">
          <BulletList items={research.risks} />
        </Section>
      </Grid>
      <Section title="Assumptions to verify">
        <BulletList items={research.assumptions_to_verify} />
      </Section>
    </div>
  )
}

function SourceChips({ ids }) {
  const { ids: valid, openSource } = useCitations()
  const shown = ids.filter((id) => valid.has(id))
  if (!shown.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((id) => (
        <a
          key={id}
          href={`#source-${id}`}
          onClick={(e) => {
            if (!openSource) return
            e.preventDefault()
            openSource(id)
          }}
          className="rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-neutral-400 transition hover:border-neutral-500 hover:text-white"
        >
          Source {id}
        </a>
      ))}
    </div>
  )
}

export function CompetitorsPanel({ competitors }) {
  if (!competitors) return MISSING
  const { competitors: list, alternatives, differentiation, market_gaps, unverified_competitors } = competitors
  return (
    <div className="space-y-4">
      {list.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {list.map((c) => (
            <Section key={c.name}>
              <div className="mb-3 flex items-start justify-between gap-3">
                <h3 className="text-base font-medium text-white">{c.name}</h3>
                <SourceChips ids={c.source_ids} />
              </div>
              <p className="mb-4 text-sm leading-relaxed text-neutral-400">
                <CitedText text={c.description} />
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="mb-2 text-xs uppercase tracking-widest text-neutral-600">Strengths</p>
                  <BulletList items={c.strengths} />
                </div>
                <div>
                  <p className="mb-2 text-xs uppercase tracking-widest text-neutral-600">Weaknesses</p>
                  <BulletList items={c.weaknesses} />
                </div>
              </div>
            </Section>
          ))}
        </div>
      ) : (
        <EmptyState>
          No competitors could be verified. A competitor is only listed when a retrieved web source names it.
        </EmptyState>
      )}
      {unverified_competitors?.length > 0 && (
        <p className="px-1 text-xs leading-relaxed text-neutral-500">
          Omitted because no retrieved source mentions them: {unverified_competitors.join(', ')}.
        </p>
      )}
      <Grid>
        <Section title="How customers cope today">
          <BulletList items={alternatives} />
        </Section>
        <Section title="Market gaps">
          <BulletList items={market_gaps} />
        </Section>
      </Grid>
      <Section title="Differentiation">
        <BulletList items={differentiation} />
      </Section>
    </div>
  )
}

const PRIORITIES = [
  { id: 'must', label: 'Must have' },
  { id: 'should', label: 'Should have' },
  { id: 'could', label: 'Could have' },
]

export function ProductPanel({ product }) {
  if (!product) return MISSING
  return (
    <div className="space-y-4">
      <Section title="Vision">
        <p className="text-xl font-medium leading-snug tracking-tight text-white">{product.product_vision}</p>
      </Section>
      <Section title="MVP features">
        <div className="grid gap-6 md:grid-cols-3">
          {PRIORITIES.map((p) => {
            const features = product.mvp_features.filter((f) => f.priority === p.id)
            return (
              <div key={p.id}>
                <p className="mb-3 text-xs text-neutral-500">
                  {p.label} <span className="font-mono text-neutral-700">· {features.length}</span>
                </p>
                <ul className="space-y-3">
                  {features.map((f) => (
                    <li key={f.name} className="border-l border-line-strong pl-3">
                      <p className="text-sm text-white">{f.name}</p>
                      <p className="text-sm leading-relaxed text-neutral-500">{f.description}</p>
                    </li>
                  ))}
                  {!features.length && <li className="text-sm text-neutral-700">—</li>}
                </ul>
              </div>
            )
          })}
        </div>
      </Section>
      <Grid>
        <Section title="Core user journey">
          <BulletList items={product.user_journey} ordered />
        </Section>
        <Section title="Differentiators">
          <BulletList items={product.differentiators} />
        </Section>
        <Section title="Success metrics">
          <BulletList items={product.success_metrics} />
        </Section>
        <Section title="Pricing options">
          <BulletList items={product.pricing_options} />
        </Section>
      </Grid>
      <Section title="Build risks">
        <BulletList items={product.build_risks} />
      </Section>
    </div>
  )
}

function hostname(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function SourcesPanel({ citations, retrieval, highlight }) {
  return (
    <Section>
      {citations.length ? (
        <ol className="divide-y divide-line">
          {citations.map((c) => (
            <li
              key={c.id}
              id={`source-${c.id}`}
              className={`flex scroll-mt-28 gap-4 py-4 text-sm transition-colors first:pt-0 last:pb-0 ${
                highlight === c.id ? 'bg-white/[0.04]' : ''
              }`}
            >
              <span className="w-6 shrink-0 font-mono text-xs leading-6 text-neutral-500">{c.id}</span>
              <div className="min-w-0 space-y-1.5">
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-white underline decoration-neutral-700 underline-offset-4 transition hover:decoration-white"
                >
                  {c.title}
                </a>
                <p className="font-mono text-xs text-neutral-600">{hostname(c.url)}</p>
                {c.snippet && <p className="leading-relaxed text-neutral-400">“{c.snippet}”</p>}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-sm text-neutral-500">No sources were retrieved for this report.</p>
      )}
      {retrieval?.queries?.length > 0 && (
        <p className="mt-5 border-t border-line pt-4 text-xs leading-relaxed text-neutral-600">
          Searched: {retrieval.queries.map((q) => `“${q}”`).join(' · ')}
        </p>
      )}
    </Section>
  )
}
