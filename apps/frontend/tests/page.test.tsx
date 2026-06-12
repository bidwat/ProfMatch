import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import Home from '../app/page'

const pushMock = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: jest.fn(), prefetch: jest.fn() }),
}))

beforeEach(() => {
  pushMock.mockClear()
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        database_path: 'firestore',
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
  it('renders the search-first public landing page', async () => {
    render(<Home />)

    expect(screen.getByText(/Find professors whose recent work matches/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Professor, university, department/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Robotics' })).toBeInTheDocument()
    expect(screen.getAllByText('Browse professors').length).toBeGreaterThan(0)
    expect(screen.getByText('Match preview')).toBeInTheDocument()
    expect(screen.getByText(/What does the match percentage mean/)).toBeInTheDocument()
    expect(await screen.findByText('890')).toBeInTheDocument()
    expect(screen.queryByText('Stanford University')).not.toBeInTheDocument()
  })

  it('routes hero searches to the public discover page', async () => {
    const { fireEvent } = await import('@testing-library/react')
    render(<Home />)

    fireEvent.change(screen.getByPlaceholderText(/Professor, university/), { target: { value: 'climate modeling' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(pushMock).toHaveBeenCalledWith('/professors?q=climate%20modeling')

    fireEvent.click(screen.getByRole('button', { name: 'Robotics' }))
    expect(pushMock).toHaveBeenCalledWith('/professors?q=Robotics')
  })
})
