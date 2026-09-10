import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';
import Login from './Login.jsx';

const navigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

describe('Login page', () => {
  beforeEach(() => {
    navigate.mockReset();
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    supabase.auth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    });
    supabase.auth.signInWithOAuth.mockResolvedValue({ error: null });
  });

  it('renders the Google login button', async () => {
    renderLogin();
    expect(await screen.findByRole('button', { name: /Continue with Google/i })).toBeInTheDocument();
  });

  it('clicking Google login calls signInWithOAuth', async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(await screen.findByRole('button', { name: /Continue with Google/i }));
    await waitFor(() => {
      expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
        expect.objectContaining({ provider: 'google' }),
      );
    });
  });

  it('redirectTo uses VITE_SITE_URL', async () => {
    vi.stubEnv('VITE_SITE_URL', 'http://localhost:5173');
    const user = userEvent.setup();
    renderLogin();
    await user.click(await screen.findByRole('button', { name: /Continue with Google/i }));
    await waitFor(() => {
      expect(supabase.auth.signInWithOAuth).toHaveBeenCalled();
    });
    const arg = supabase.auth.signInWithOAuth.mock.calls[0][0];
    expect(arg.options.redirectTo).toBe('http://localhost:5173/login');
  });

  it('navigates to /onboarding on SIGNED_IN', async () => {
    supabase.auth.onAuthStateChange.mockImplementation((cb) => {
      cb('SIGNED_IN', { user: { email: 'a@b.com' } });
      return { data: { subscription: { unsubscribe: vi.fn() } } };
    });
    renderLogin();
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/onboarding', { replace: true });
    });
  });

  it('navigates to /onboarding if a session already exists on mount', async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { email: 'a@b.com' } } },
    });
    renderLogin();
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/onboarding', { replace: true });
    });
  });
});
