import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AppShell from './AppShell.jsx';
import { useGmailStatus } from '../../hooks/useGmailStatus.js';
import { useAuth } from '../../hooks/useAuth.js';

vi.mock('../../hooks/useAuth.js', () => ({ useAuth: vi.fn() }));

function renderShell(path = '/matches') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell>
        <div>Page content</div>
      </AppShell>
    </MemoryRouter>,
  );
}

describe('AppShell navigation', () => {
  beforeEach(() => {
    useGmailStatus.mockReturnValue({
      status: { connected: false, email: null },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    useAuth.mockReturnValue({ user: null, loading: false, signOut: vi.fn() });
  });

  it('renders the navbar with brand and page links', () => {
    renderShell();
    expect(screen.getByText('FindMyProfessor')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Research Matches' })).toHaveAttribute('href', '/matches');
    expect(screen.getByRole('link', { name: 'Outreach' })).toHaveAttribute('href', '/outreach/history');
    expect(screen.getByText('Page content')).toBeInTheDocument();
  });

  it('shows a green Gmail status when connected', () => {
    useGmailStatus.mockReturnValue({
      status: { connected: true, email: 'me@gmail.com' },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    renderShell();
    expect(document.querySelector('.status-dot.green')).toBeTruthy();
    expect(screen.getByText('me@gmail.com')).toBeInTheDocument();
  });

  it('shows a gray Gmail status when not connected', () => {
    renderShell();
    expect(document.querySelector('.status-dot.grey')).toBeTruthy();
    expect(document.querySelector('.status-dot.green')).toBeFalsy();
  });

  describe('auth session hydration', () => {
    it('does not show "Sign in" while the session is still loading, even with no user yet', () => {
      // This is the exact false-negative that flashes "Sign in" for an
      // already-authenticated production user: getSession() is async, so
      // `user` is null on the very first render regardless of whether a
      // session actually exists. The account area must stay neutral until
      // loading resolves, never assume "no user yet" means "signed out".
      useAuth.mockReturnValue({ user: null, loading: true, signOut: vi.fn() });
      renderShell();
      expect(screen.queryByText('Sign in')).not.toBeInTheDocument();
    });

    it('shows the account avatar once an authenticated session has hydrated', () => {
      useAuth.mockReturnValue({
        user: { email: 'student@example.com' },
        loading: false,
        signOut: vi.fn(),
      });
      renderShell();
      expect(screen.queryByText('Sign in')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Account menu' })).toBeInTheDocument();
    });

    it('shows "Sign in" once loading has resolved with no session', () => {
      useAuth.mockReturnValue({ user: null, loading: false, signOut: vi.fn() });
      renderShell();
      expect(screen.getByText('Sign in')).toBeInTheDocument();
    });

    it('transitions correctly from loading to an authenticated session on refresh-like hydration', () => {
      useAuth.mockReturnValue({ user: null, loading: true, signOut: vi.fn() });
      const { rerender } = render(
        <MemoryRouter initialEntries={['/matches']}>
          <AppShell><div>Page content</div></AppShell>
        </MemoryRouter>,
      );
      expect(screen.queryByText('Sign in')).not.toBeInTheDocument();

      useAuth.mockReturnValue({
        user: { email: 'student@example.com' },
        loading: false,
        signOut: vi.fn(),
      });
      rerender(
        <MemoryRouter initialEntries={['/matches']}>
          <AppShell><div>Page content</div></AppShell>
        </MemoryRouter>,
      );
      expect(screen.queryByText('Sign in')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Account menu' })).toBeInTheDocument();
    });
  });
});
