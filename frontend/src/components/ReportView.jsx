import { motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useState } from 'react'

import FactCheckPanel from './report/FactCheckPanel'
import FinancePanel from './report/FinancePanel'
import { CompetitorsPanel, MarketPanel, OverviewPanel, ProductPanel, SourcesPanel } from './report/panels'
import { CitationContext } from './report/citations'

function unverifiedReason(retrieval) {
  switch (retrieval?.status) {
    case 'disabled':
      return 'Web search is turned off (TAVILY_API_KEY is not set), so no web sources were retrieved.'
    case 'failed':
      return `Web search failed${retrieval.detail ? ` (${retrieval.detail})` : ''}, so no web sources were retrieved.`
    case 'no_results':
      return 'Web search returned no results, so no web sources were retrieved.'
    case 'ok':
      return 'Web sources were retrieved, but the agents did not cite any of them.'
    default:
      return 'No web sources were retrieved.'
  }
}

function ProvenanceNote({ data }) {
  const sourced = data.data_provenance === 'web_sources'
  return (
    <div
      role="note"
      className={`flex gap-3 border-l-2 py-1 pl-4 text-sm leading-relaxed ${
        sourced ? 'border-neutral-600 text-neutral-400' : 'border-yellow-500/70 text-neutral-300'
      }`}
    >
      <p>
        {sourced
          ? "Bracketed numbers link to the web sources the agents cited. Open a source to confirm it supports the claim. Statements without a number are the model's own analysis."
          : `${unverifiedReason(data.retrieval)} This brief was written from the model's general knowledge, so it has no citations and contains no verified statistics.`}
      </p>
    </div>
  )
}

export default function ReportView({ data, onRecalculateFinance }) {
  const { report, citations = [], retrieval, request, model, generated_at } = data
  const [tab, setTab] = useState('overview')
  const [highlight, setHighlight] = useState(null)

  const ids = useMemo(() => new Set(citations.map((c) => c.id)), [citations])
  const openSource = useCallback((id) => {
    setTab('sources')
    setHighlight(id)
  }, [])

  useEffect(() => {
    if (tab !== 'sources' || highlight == null) return
    document.getElementById(`source-${highlight}`)?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  }, [tab, highlight])

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'market', label: 'Market' },
    { id: 'competitors', label: 'Competitors', count: data.competitors?.competitors.length },
    { id: 'product', label: 'Product' },
    { id: 'financials', label: 'Financials' },
    {
      id: 'factcheck',
      label: 'Fact check',
      count: data.fact_check ? data.fact_check.removed_citations + data.fact_check.figure_flags.length : 0,
    },
    { id: 'sources', label: 'Sources', count: citations.length },
  ]

  return (
    <CitationContext.Provider value={{ ids, openSource }}>
      <div className="space-y-8">
        <motion.header initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          <h1 className="text-4xl font-semibold tracking-tighter text-white sm:text-5xl">{report.title}</h1>
          <p className="max-w-3xl text-lg leading-relaxed text-neutral-400">{request.idea}</p>
          <p className="font-mono text-xs text-neutral-600">
            {new Date(generated_at).toLocaleString()} · {model}
          </p>
          <ProvenanceNote data={data} />
        </motion.header>

        <nav
          role="tablist"
          aria-label="Report sections"
          className="sticky top-[57px] z-[5] -mx-4 flex gap-1 overflow-x-auto border-b border-line bg-black/90 px-4 backdrop-blur sm:mx-0 sm:px-0"
        >
          {tabs.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => {
                setTab(t.id)
                setHighlight(null)
              }}
              className={`relative whitespace-nowrap px-3 py-3 text-sm transition ${
                tab === t.id ? 'text-white' : 'text-neutral-500 hover:text-neutral-200'
              }`}
            >
              {t.label}
              {t.count > 0 && <span className="ml-1.5 font-mono text-xs text-neutral-600">{t.count}</span>}
              {tab === t.id && (
                <motion.span layoutId="tab-underline" className="absolute inset-x-3 -bottom-px h-px bg-white" />
              )}
            </button>
          ))}
        </nav>

        <motion.div
          key={tab}
          role="tabpanel"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {tab === 'overview' && (
            <OverviewPanel report={report} factCheck={data.fact_check} onOpenFactCheck={() => setTab('factcheck')} />
          )}
          {tab === 'market' && <MarketPanel research={data.research} />}
          {tab === 'competitors' && <CompetitorsPanel competitors={data.competitors} />}
          {tab === 'product' && <ProductPanel product={data.product} />}
          {tab === 'financials' && <FinancePanel finance={data.finance} onRecalculate={onRecalculateFinance} />}
          {tab === 'factcheck' && <FactCheckPanel factCheck={data.fact_check} />}
          {tab === 'sources' && <SourcesPanel citations={citations} retrieval={retrieval} highlight={highlight} />}
        </motion.div>
      </div>
    </CitationContext.Provider>
  )
}
