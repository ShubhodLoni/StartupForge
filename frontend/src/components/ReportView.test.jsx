import { fireEvent, render, screen } from '@testing-library/react'

import { report } from '../test/fixtures'
import ReportView from './ReportView'

const unsourced = {
  ...report,
  citations: [],
  competitors: { ...report.competitors, competitors: [] },
  retrieval: undefined,
  data_provenance: 'llm_knowledge_unverified',
}

const openTab = (name) => fireEvent.click(screen.getByRole('tab', { name: new RegExp(`^${name}`) }))

describe('ReportView', () => {
  it('renders the overview by default', () => {
    render(<ReportView data={report} />)
    expect(screen.getByRole('heading', { name: 'ClinicFlow' })).toBeInTheDocument()
    expect(screen.getByText('Pilot with 5 clinics')).toBeInTheDocument()
    expect(screen.getByText('Base case projects growth under editable assumptions.')).toBeInTheDocument()
  })

  it('is explicit that there are no sources instead of inventing any', () => {
    render(<ReportView data={unsourced} />)
    expect(screen.getByRole('note')).toHaveTextContent(/no web sources were retrieved/i)
    openTab('Sources')
    expect(screen.getByText(/no sources were retrieved/i)).toBeInTheDocument()
    expect(screen.queryAllByRole('link')).toHaveLength(0)
  })

  it('explains why there are no sources when search is disabled', () => {
    render(<ReportView data={{ ...unsourced, retrieval: { status: 'disabled', queries: [] } }} />)
    expect(screen.getByRole('note')).toHaveTextContent(/TAVILY_API_KEY is not set/)
  })

  it('clicking a citation opens the matching source', () => {
    render(<ReportView data={report} />)
    fireEvent.click(screen.getByRole('link', { name: 'Source 1' }))
    expect(screen.getByRole('tab', { name: /^Sources/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('link', { name: 'Source A' })).toHaveAttribute('href', 'https://www.example.org/a')
    expect(screen.getByText('“Verbatim excerpt”')).toBeInTheDocument()
    expect(screen.getByText('example.org')).toBeInTheDocument()
    expect(screen.getByText(/dental missed calls/)).toBeInTheDocument()
  })

  it('shows verified competitors and lists omitted ones', () => {
    render(<ReportView data={report} />)
    openTab('Competitors')
    expect(screen.getByRole('heading', { name: 'Acme Reception' })).toBeInTheDocument()
    expect(screen.getByText(/no retrieved source mentions them: Ghost Corp/)).toBeInTheDocument()
  })

  it('groups product features by priority', () => {
    render(<ReportView data={report} />)
    openTab('Product')
    expect(screen.getByText('Never miss a patient call.')).toBeInTheDocument()
    expect(screen.getByText('Call answering')).toBeInTheDocument()
    expect(screen.getByText('SMS reminders')).toBeInTheDocument()
  })

  it('summarizes the fact check on the overview and opens the tab', () => {
    render(<ReportView data={report} />)
    fireEvent.click(screen.getByRole('button', { name: /fact check: 3 cited claims checked/i }))
    expect(screen.getByRole('tab', { name: /^Fact check/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Citation removed')).toBeInTheDocument()
    expect(screen.getByText(/Figure has no source/)).toBeInTheDocument()
  })

  it('handles reports saved before newer sections existed', () => {
    const old = { ...unsourced, competitors: undefined, product: undefined, finance: undefined, fact_check: undefined }
    render(<ReportView data={old} />)
    openTab('Financials')
    expect(screen.getByText(/not available for this report/i)).toBeInTheDocument()
    openTab('Fact check')
    expect(screen.getByText(/not available for this report/i)).toBeInTheDocument()
  })
})
