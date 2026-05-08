import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import AppShell from '../components/AppShell'
import ProfilePage from '../app/profile/page'

let pathname = '/'
const replace = jest.fn()
const push = jest.fn()

jest.mock('next/navigation', () => ({
  usePathname: () => pathname,
  useRouter: () => ({ replace, push }),
}))

jest.mock('@/lib/api', () => ({
  getCurrentUser: jest.fn(),
  getUserState: jest.fn(),
  logoutUser: jest.fn(),
  deleteAccount: jest.fn(),
  findMatches: jest.fn(),
  patchUserState: jest.fn(),
}))

const api = jest.requireMock('@/lib/api')

beforeEach(() => {
  localStorage.clear()
  replace.mockClear()
  push.mockClear()
  api.getCurrentUser.mockReset()
  api.getUserState.mockReset()
  api.logoutUser.mockReset()
  api.deleteAccount.mockReset()
  api.findMatches.mockReset()
  api.patchUserState.mockReset()
})

describe('UX shell and profile states', () => {
  it('renders public routes without authenticated top navigation', async () => {
    pathname = '/'
    api.getCurrentUser.mockRejectedValue(new Error('not signed in'))

    render(<AppShell><div>Public landing content</div></AppShell>)

    expect(screen.getByText('Public landing content')).toBeInTheDocument()
    expect(screen.queryByText('Home')).not.toBeInTheDocument()
    expect(screen.queryByText('Matches')).not.toBeInTheDocument()
  })

  it('renders authenticated top navigation and admin link for admin users', async () => {
    pathname = '/dashboard'
    api.getCurrentUser.mockResolvedValue({ user: { display_name: 'Admin User', email: 'admin@example.edu', created_at: '2026-05-06T00:00:00', role: 'admin' } })
    api.getUserState.mockResolvedValue({})

    render(<AppShell><div>Dashboard content</div></AppShell>)

    expect(await screen.findByText('Admin User')).toBeInTheDocument()
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Matches')).toBeInTheDocument()
    expect(screen.getByText('Discover')).toBeInTheDocument()
    expect(screen.getByText('Saved')).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('keeps Update and match available so profile saves always send requests', async () => {
    pathname = '/profile'
    api.getCurrentUser.mockRejectedValue(new Error('not signed in'))
    api.getUserState.mockRejectedValue(new Error('not signed in'))

    render(<ProfilePage />)

    const button = screen.getByRole('button', { name: /Update and match/i })
    await waitFor(() => expect(button).toBeEnabled())
  })
})
