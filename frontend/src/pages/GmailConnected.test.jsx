import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GmailConnected from './GmailConnected.jsx';
import { savePendingIntent } from '../services/gmail.js';

const navigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => navigate };
});

function renderPage() {
  return render(
    <MemoryRouter>
      <GmailConnected />
    </MemoryRouter>,
  );
}

describe('Gmail connected page', () => {
  beforeEach(() => {
    navigate.mockReset();
    localStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders Gmail Connected!', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /Gmail Connected!/i })).toBeInTheDocument();
  });

  it('reads pending intent from localStorage and navigates after 1.5s', () => {
    savePendingIntent('prof-1', '/outreach/compose/prof-1', 'draft-1');
    renderPage();
    // Deliberately NOT cleared here — the compose page it hands off to owns
    // clearing it, since it needs the draft_id to restore the in-progress draft.
    expect(localStorage.getItem('fmp_pending_outreach')).not.toBeNull();

    act(() => { vi.advanceTimersByTime(1499); });
    expect(navigate).not.toHaveBeenCalled();

    act(() => { vi.advanceTimersByTime(1); });
    expect(navigate).toHaveBeenCalledWith('/outreach/compose/prof-1', { replace: true });
  });

  it('falls back to /outreach/history after 2s when no intent exists', () => {
    renderPage();
    act(() => { vi.advanceTimersByTime(1999); });
    expect(navigate).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1); });
    expect(navigate).toHaveBeenCalledWith('/outreach/history', { replace: true });
  });

  it('prefers return_to from the URL over localStorage (survives even without a pending intent)', () => {
    // This is the server-verified channel: the backend attaches ?return_to=
    // from the OAuth state token, so it works even if localStorage was lost
    // somewhere across the round trip (a different tab, private browsing,
    // storage partitioning).
    render(
      <MemoryRouter initialEntries={['/outreach/gmail-connected?return_to=%2Foutreach%2Fcompose%2Fprof-9']}>
        <GmailConnected />
      </MemoryRouter>,
    );
    act(() => { vi.advanceTimersByTime(1500); });
    expect(navigate).toHaveBeenCalledWith('/outreach/compose/prof-9', { replace: true });
  });

  it('ignores an unsafe return_to and falls back to /outreach/history', () => {
    render(
      <MemoryRouter initialEntries={['/outreach/gmail-connected?return_to=https%3A%2F%2Fevil.example.com']}>
        <GmailConnected />
      </MemoryRouter>,
    );
    act(() => { vi.advanceTimersByTime(2000); });
    expect(navigate).toHaveBeenCalledWith('/outreach/history', { replace: true });
  });

  it('is StrictMode-safe: still returns to the exact draft under real double-invocation', () => {
    // React.StrictMode double-invokes the lazy useState initialiser (and
    // effects) once on mount, in development. If the initialiser both reads
    // AND clears the pending intent, the second invocation sees it already
    // gone and the user is dropped on a fallback page instead of their draft.
    savePendingIntent('prof-1', '/outreach/compose/prof-1');
    render(
      <MemoryRouter>
        <React.StrictMode>
          <GmailConnected />
        </React.StrictMode>
      </MemoryRouter>,
    );

    act(() => { vi.advanceTimersByTime(1500); });
    expect(navigate).toHaveBeenCalledWith('/outreach/compose/prof-1', { replace: true });
  });
});
