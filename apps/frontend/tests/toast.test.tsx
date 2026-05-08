import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { Toast } from '../components/Toast'

describe('Toast', () => {
  it('renders the hi-fi toast notification surface', () => {
    render(<Toast message="Saved to shortlist" tone="success" />)
    expect(screen.getByRole('status')).toHaveTextContent('Saved to shortlist')
  })
})
