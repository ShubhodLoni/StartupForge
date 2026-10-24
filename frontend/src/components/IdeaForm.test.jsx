import { fireEvent, render, screen } from '@testing-library/react'

import IdeaForm from './IdeaForm'

describe('IdeaForm', () => {
  it('blocks submission of a too-short idea', () => {
    const onSubmit = vi.fn()
    render(<IdeaForm onSubmit={onSubmit} />)
    fireEvent.change(screen.getByLabelText('Startup idea'), { target: { value: 'short' } })
    fireEvent.click(screen.getByRole('button', { name: /analyze idea/i }))
    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument()
  })

  it('submits trimmed values and nulls empty optional fields', () => {
    const onSubmit = vi.fn()
    render(<IdeaForm onSubmit={onSubmit} />)
    fireEvent.change(screen.getByLabelText('Startup idea'), {
      target: { value: '  AI receptionist for dental clinics  ' },
    })
    fireEvent.change(screen.getByLabelText(/industry/i), { target: { value: ' Healthcare ' } })
    fireEvent.click(screen.getByRole('button', { name: /analyze idea/i }))
    expect(onSubmit).toHaveBeenCalledWith({
      idea: 'AI receptionist for dental clinics',
      industry: 'Healthcare',
      target_market: null,
    })
  })
})
