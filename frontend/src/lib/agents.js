import { Boxes, Calculator, FileText, Globe, Search, ShieldCheck, Swords } from 'lucide-react'

import { usd } from './format'

export const AGENTS = [
  { id: 'search', name: 'Search', description: 'Plans queries, fetches and indexes pages', icon: Globe },
  { id: 'research', name: 'Research', description: 'Customers, pain points, trends, risks', icon: Search },
  { id: 'competitor', name: 'Competitor', description: 'Verifies competitors against sources', icon: Swords },
  { id: 'product', name: 'Product', description: 'MVP scope, user journey, metrics', icon: Boxes },
  { id: 'finance', name: 'Finance', description: 'Assumptions → deterministic projections', icon: Calculator },
  { id: 'report', name: 'Report', description: 'Writes the founder-ready brief', icon: FileText },
  { id: 'critic', name: 'Critic', description: 'Fact-checks citations and figures', icon: ShieldCheck },
]

const RETRIEVAL_SUMMARY = {
  disabled: 'Web search off (no TAVILY_API_KEY)',
  failed: 'Web search failed',
  no_results: 'No web results found',
}

export const plural = (n, word) => `${n} ${word}${n === 1 ? '' : /(s|sh|ch|x)$/.test(word) ? 'es' : 's'}`

export function summarizeAgentOutput(agent, output) {
  if (agent === 'search') {
    const r = output?.retrieval
    if (r?.status === 'ok') {
      if (r.mode === 'rag') return `${plural(r.pages, 'page')} → ${plural(r.chunks, 'passage')} indexed`
      return `${plural(output.sources.length, 'source')} from ${plural(r.queries.length, 'search')}`
    }
    return RETRIEVAL_SUMMARY[r?.status] || null
  }
  if (agent === 'competitor' && output?.competitors) {
    return plural(output.competitors.competitors.length, 'verified competitor')
  }
  if (agent === 'product' && output?.product) {
    return plural(output.product.mvp_features.length, 'MVP feature')
  }
  if (agent === 'finance' && output?.finance) {
    const base = output.finance.scenarios.find((s) => s.name === 'base')
    if (base) return `Base case: ${usd(base.projection.metrics.ending_mrr)} MRR at month ${base.projection.rows.length}`
  }
  if (agent === 'critic' && output?.fact_check) {
    const fc = output.fact_check
    return `${plural(fc.claims_checked, 'claim')} checked · ${plural(fc.removed_citations, 'citation')} removed`
  }
  return null
}
