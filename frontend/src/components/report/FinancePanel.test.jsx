import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { finance } from '../../test/fixtures'
import FinancePanel from './FinancePanel'

describe('FinancePanel', () => {
  it('shows base-scenario KPIs from the computed model', () => {
    render(<FinancePanel finance={finance} onRecalculate={async () => {}} />)
    expect(screen.getByText('MRR at month 24')).toBeInTheDocument()
    expect(screen.getByText('$24K')).toBeInTheDocument()
    expect(screen.getByText('Month 14')).toBeInTheDocument()
    expect(screen.getByText('13.3×')).toBeInTheDocument()
  })

  it('switches scenario', () => {
    render(<FinancePanel finance={finance} onRecalculate={async () => {}} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Conservative' }))
    expect(screen.getByText('Not reached')).toBeInTheDocument()
    expect(screen.getByText('$12K')).toBeInTheDocument()
  })

  it('shows rationale and engine corrections', () => {
    render(<FinancePanel finance={finance} onRecalculate={async () => {}} />)
    expect(screen.getByText(/typical SMB software price/)).toBeInTheDocument()
    expect(screen.getByText(/clamped to 100/)).toBeInTheDocument()
  })

  it('sends parsed assumptions to the recalculate callback', async () => {
    const onRecalculate = vi.fn(async () => {})
    render(<FinancePanel finance={finance} onRecalculate={onRecalculate} />)

    fireEvent.change(screen.getByLabelText('Price / customer / month'), { target: { value: '299' } })
    fireEvent.click(screen.getByRole('button', { name: /recalculate/i }))

    await waitFor(() => expect(onRecalculate).toHaveBeenCalled())
    expect(onRecalculate).toHaveBeenCalledWith(expect.objectContaining({ price_per_month: 299, months: 24 }))
  })

  it('shows backend errors', async () => {
    const onRecalculate = vi.fn(async () => {
      throw new Error('Input should be less than or equal to 100')
    })
    render(<FinancePanel finance={finance} onRecalculate={onRecalculate} />)
    fireEvent.click(screen.getByRole('button', { name: /recalculate/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('less than or equal to 100')
  })

  it('offers reset when assumptions differ from the agent original', () => {
    const edited = { ...finance, original_assumptions: { ...finance.assumptions, price_per_month: 99 } }
    render(<FinancePanel finance={edited} onRecalculate={async () => {}} />)
    expect(screen.getByRole('button', { name: /reset to agent/i })).toBeInTheDocument()
  })

  it('rejects non-numeric input without calling the backend', async () => {
    const onRecalculate = vi.fn()
    render(<FinancePanel finance={finance} onRecalculate={onRecalculate} />)
    fireEvent.change(screen.getByLabelText('Churn / month'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /recalculate/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Churn / month must be a number.')
    expect(onRecalculate).not.toHaveBeenCalled()
  })

  it('offers a monthly table view of the numbers', () => {
    render(<FinancePanel finance={finance} onRecalculate={async () => {}} />)
    expect(screen.getByText('Monthly table')).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(25)
  })
})
