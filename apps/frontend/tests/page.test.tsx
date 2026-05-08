import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import Home from '../app/page'

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        database_path: '/tmp/professor_match_publications.sqlite',
        professor_count: 890,
        publication_count: 4094,
        university_count: 9,
        professors_with_email: 382,
        professors_with_homepage: 608,
        professors_with_publications: 844,
        universities: [
          { university: 'Stanford University', professor_count: 39, publication_count: 180 },
        ],
      }),
    } as Response)
  ) as jest.Mock
})

afterEach(() => {
  jest.restoreAllMocks()
})

describe('Home', () => {
  it('renders the cleaned-up public landing page', async () => {
    render(<Home />)

    expect(screen.getByText(/Build a shortlist of professors/)).toBeInTheDocument()
    expect(screen.getAllByText('Get started →')).toHaveLength(2)
    expect(screen.getAllByText('Sign in')).toHaveLength(2)
    expect(screen.getByText('Match preview')).toBeInTheDocument()
    expect(await screen.findByText('Professors')).toBeInTheDocument()
    expect(await screen.findByText('890')).toBeInTheDocument()
    expect(screen.queryByText('Stanford University')).not.toBeInTheDocument()
    expect(screen.queryByText('How it works')).not.toBeInTheDocument()
  })
})
