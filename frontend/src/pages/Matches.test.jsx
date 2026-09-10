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

  it('shows an error state if the API fails', async () => {
    matching.fetchMatches.mockRejectedValue(new Error('Matching service down.'));
    renderMatches();
    expect(await screen.findByText('Failed to load matches')).toBeInTheDocument();
    expect(screen.getByText('Matching service down.')).toBeInTheDocument();
  });
});
