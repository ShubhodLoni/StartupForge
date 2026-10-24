import { render, screen } from '@testing-library/react'

import CitedText from './CitedText'

describe('CitedText', () => {
  it('turns known markers into links and drops unknown ones', () => {
    const { container } = render(<CitedText text="Claim [1, 9] and more [7]." citationIds={new Set([1])} />)
    expect(screen.getByRole('link', { name: 'Source 1' })).toHaveAttribute('href', '#source-1')
    expect(screen.queryByRole('link', { name: 'Source 9' })).not.toBeInTheDocument()
    expect(container.textContent).toBe('Claim[1] and more.')
  })

  it('leaves plain text untouched', () => {
    const { container } = render(<CitedText text="No citations here." citationIds={new Set()} />)
    expect(container.textContent).toBe('No citations here.')
  })
})
