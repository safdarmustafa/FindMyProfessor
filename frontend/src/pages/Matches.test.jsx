import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Matches from './Matches.jsx';
import { matchingResponse, matchItem } from '../test/fixtures.js';
import * as matching from '../services/matching.js';
import * as profile from '../services/profile.js';
import * as api from '../services/api.js';

vi.mock('../services/matching.js', () => ({
  fetchMatches: vi.fn(),
  fetchUniversities: vi.fn(),
  fetchProfessor: vi.fn(),
}));

vi.mock('../services/profile.js', () => ({
  fetchProfile: vi.fn(),
  updateProfile: vi.fn(),
  confirmProfile: vi.fn(),
  uploadCV: vi.fn(),
}));

vi.mock('../services/api.js', async () => {
  const actual = await vi.importActual('../services/api.js');
  return { ...actual, getProfileId: vi.fn(() => 'p1') };
});

function renderMatches() {
  return render(
    <MemoryRouter>
      <Matches />
    </MemoryRouter>,
  );
}

describe('Matches page', () => {
  beforeEach(() => {
    api.getProfileId.mockReturnValue('p1');
    profile.fetchProfile.mockResolvedValue({ confirmed: true });
    matching.fetchUniversities.mockResolvedValue({ universities: [] });
    matching.fetchMatches.mockResolvedValue(matchingResponse);
  });

  it('renders professor cards from the API response', async () => {
    renderMatches();
    expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
  });

  it('each card shows name, title, university, department, areas, score, priority, and actions', async () => {
    renderMatches();
    expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText(/Associate Professor/)).toBeInTheDocument();
    expect(screen.getByText('Stanford University')).toBeInTheDocument();
    expect(screen.getByText(/Computer Science/)).toBeInTheDocument();
    expect(screen.getAllByText('Computer Vision').length).toBeGreaterThan(0);
    expect(screen.getByText(/87% match/)).toBeInTheDocument();
    expect(screen.getByText(/High/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /View Profile/i })).toHaveAttribute(
      'href',
      `/matches/${matchItem.professor.id}`,
    );
    expect(screen.getByRole('link', { name: /Prepare Email/i })).toHaveAttribute(
      'href',
      `/outreach/compose/${matchItem.professor.id}`,
    );
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });

  it('View Profile navigates to /matches/:id', async () => {
    renderMatches();
    const link = await screen.findByRole('link', { name: /View Profile/i });
    expect(link).toHaveAttribute('href', `/matches/${matchItem.professor.id}`);
  });

  it('Prepare Email navigates to /outreach/compose/:id', async () => {
    renderMatches();
    const link = await screen.findByRole('link', { name: /Prepare Email/i });
    expect(link).toHaveAttribute('href', `/outreach/compose/${matchItem.professor.id}`);
  });

  it('search input filters cards by name', async () => {
    const user = userEvent.setup();
    matching.fetchMatches.mockResolvedValue({
      ...matchingResponse,
      count: 2,
      matches: [
        matchItem,
        {
          ...matchItem,
          professor: { ...matchItem.professor, id: 'other', name: 'Alan Turing', first_name: 'Alan', last_name: 'Turing' },
        },
      ],
    });
    renderMatches();
    expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('Alan Turing')).toBeInTheDocument();

    const search = screen.getByPlaceholderText(/search/i);
    await user.type(search, 'Jane');

    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.queryByText('Alan Turing')).not.toBeInTheDocument();
  });

  it('shows an empty state when there are no matches', async () => {
    matching.fetchMatches.mockResolvedValue({ matches: [] });
    renderMatches();
    expect(await screen.findByText(/No matches found/i)).toBeInTheDocument();
  });

  it('shows a loading skeleton while fetching', async () => {
    let resolveMatches;
    matching.fetchMatches.mockReturnValue(new Promise(r => { resolveMatches = r; }));
    renderMatches();
    expect(document.querySelector('.skeleton')).toBeTruthy();
    resolveMatches(matchingResponse);
    expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
  });

  it('shows an error state only after both the initial attempt and the automatic retry fail', async () => {
    matching.fetchMatches.mockRejectedValue(new Error('Matching service down.'));
    const callsBefore = matching.fetchMatches.mock.calls.length;
    renderMatches();
    expect(await screen.findByText('Failed to load matches', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('Matching service down.')).toBeInTheDocument();
    expect(matching.fetchMatches.mock.calls.length - callsBefore).toBe(2);
  });

  it('recovers automatically from a single transient matching failure — no user action needed', async () => {
    // Production is a real cross-origin request to a cold-startable Render
    // backend: the first request can fail even though the service is fine.
    // This is the "matching needs multiple attempts" report — the fix is a
    // single bounded automatic retry, not asking the user to click again.
    let calls = 0;
    matching.fetchMatches.mockImplementation(() => {
      calls += 1;
      if (calls === 1) return Promise.reject(new Error('cold start'));
      return Promise.resolve(matchingResponse);
    });
    renderMatches();
    expect(await screen.findByText('Jane Smith', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.queryByText('Failed to load matches')).not.toBeInTheDocument();
    expect(calls).toBe(2);
  });

  describe('profile completeness check', () => {
    it('a genuine confirmed:false response shows the incomplete-profile state', async () => {
      profile.fetchProfile.mockResolvedValue({ confirmed: false });
      renderMatches();
      expect(await screen.findByText('Confirm your CV profile')).toBeInTheDocument();
    });

    it('confirmed:true renders the normal matches page', async () => {
      profile.fetchProfile.mockResolvedValue({ confirmed: true });
      renderMatches();
      expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
      expect(screen.queryByText('Confirm your CV profile')).not.toBeInTheDocument();
    });

    it('a failed /profile request does NOT show the incomplete-profile state — matches still render', async () => {
      // This is the exact production scenario: /matching/professors succeeds
      // independently while /profile happens to fail for an unrelated
      // transient reason (network, CORS, cold start). The page must not
      // punish a working request with an incorrect "complete your profile".
      profile.fetchProfile.mockRejectedValue(new Error('Network error'));
      renderMatches();
      expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
      expect(screen.queryByText('Confirm your CV profile')).not.toBeInTheDocument();
    });

    it('an already-completed profile does not enter a "complete your profile" loop after a failed re-check', async () => {
      profile.fetchProfile.mockRejectedValue(new Error('Network error'));
      renderMatches();
      await screen.findByText('Jane Smith');
      // profileConfirmed was never actually set to false, so nothing can
      // flip the page into the incomplete-profile empty state later.
      expect(screen.queryByText('Confirm your CV profile')).not.toBeInTheDocument();
    });
  });
});
