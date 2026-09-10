import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OutreachHistory from './OutreachHistory.jsx';
import { historyItem, PROF_ID } from '../test/fixtures.js';
import * as outreach from '../services/outreach.js';
import * as api from '../services/api.js';

vi.mock('../services/outreach.js', () => ({
  listHistory: vi.fn(),
  generateDraft: vi.fn(),
  saveDraft: vi.fn(),
  sendDraft: vi.fn(),
  getDraft: vi.fn(),
  listCvVersions: vi.fn(),
  attachCv: vi.fn(),
  getSendPreview: vi.fn(),
}));

vi.mock('../services/api.js', async () => {
  const actual = await vi.importActual('../services/api.js');
  return { ...actual, getProfileId: vi.fn(() => 'p1') };
});

function renderHistory() {
  return render(
    <MemoryRouter>
      <OutreachHistory />
    </MemoryRouter>,
  );
}

describe('Outreach history page', () => {
  beforeEach(() => {
    api.getProfileId.mockReturnValue('p1');
  });

  it('renders nested professor and university .name fields', async () => {
    outreach.listHistory.mockResolvedValue([{
      ...historyItem,
      professor_name: { id: 'p1', name: 'Jane Smith' },
      university_name: { id: 'u1', name: 'Stanford University' },
    }]);
    renderHistory();
    expect((await screen.findAllByText('Jane Smith')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Stanford University').length).toBeGreaterThan(0);
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });

  it('renders outreach rows from the API', async () => {
    outreach.listHistory.mockResolvedValue([historyItem]);
    renderHistory();
    expect((await screen.findAllByText('Jane Smith')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Stanford University').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Research inquiry from a CS student').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Ready').length).toBeGreaterThan(0);
  });

  it('renders Draft, Ready, Sent, and Failed status badges', async () => {
    outreach.listHistory.mockResolvedValue([
      { ...historyItem, draft_id: '1', status: 'generated', subject: 'A' },
      { ...historyItem, draft_id: '2', status: 'ready', subject: 'B' },
      { ...historyItem, draft_id: '3', status: 'sent', subject: 'C', sent_at: '2026-09-02T00:00:00Z' },
      { ...historyItem, draft_id: '4', status: 'failed', subject: 'D' },
    ]);
    renderHistory();
    expect(await screen.findAllByText('Draft')).not.toHaveLength(0);
    expect(screen.getAllByText('Ready').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Sent').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Failed').length).toBeGreaterThan(0);
  });

  it('renders empty state when there is no history', async () => {
    outreach.listHistory.mockResolvedValue([]);
    renderHistory();
    expect(await screen.findByText(/No outreach/i)).toBeInTheDocument();
    expect(screen.getByText(/Start by finding a professor match/i)).toBeInTheDocument();
  });

  it('shows an error if the API fails', async () => {
    outreach.listHistory.mockRejectedValue(new Error('History unavailable.'));
    renderHistory();
    expect(await screen.findByText('Failed to load history')).toBeInTheDocument();
    expect(screen.getByText('History unavailable.')).toBeInTheDocument();
  });

  it('row action links back to compose', async () => {
    outreach.listHistory.mockResolvedValue([{ ...historyItem, professor_id: PROF_ID }]);
    renderHistory();
    const link = await screen.findByRole('link', { name: /Compose again/i });
    expect(link).toHaveAttribute('href', `/outreach/compose/${PROF_ID}`);
  });
});
