import { render, screen, within } from '@testing-library/react'

import { report } from '../../test/fixtures'
import { CitationContext } from './citations'
import FactCheckPanel from './FactCheckPanel'

function renderPanel(openSource = vi.fn()) {
  return render(
    <CitationContext.Provider value={{ ids: new Set([1]), openSource }}>
      <FactCheckPanel factCheck={report.fact_check} />
    </CitationContext.Provider>,
  )
}

describe('FactCheckPanel', () => {
  it('lists unsupported verdicts first, each with a text label', () => {
    renderPanel()
    const review = screen.getByRole('heading', { name: 'Claim review' }).parentElement
    const labels = within(review).getAllByRole('listitem').map((li) => li.textContent)
    expect(labels[0]).toMatch(/^Citation removed/)
    expect(labels[1]).toMatch(/^Partly supported/)
    expect(labels[2]).toMatch(/^Supported/)
  })

  it('shows flagged figures with their issue', () => {
    renderPanel()
    expect(screen.getByText('$9 billion')).toBeInTheDocument()
    expect(screen.getByText(/Figure has no source/)).toBeInTheDocument()
    expect(screen.getByText('Research Market Summary')).toBeInTheDocument()
  })

  it('links only to sources that are still cited', () => {
    renderPanel()
    expect(screen.getAllByRole('link', { name: 'Source 1' })).toHaveLength(2)
    expect(screen.queryByRole('link', { name: 'Source 2' })).not.toBeInTheDocument()
    expect(screen.getByText('Source 2')).toBeInTheDocument()
  })
})
