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
