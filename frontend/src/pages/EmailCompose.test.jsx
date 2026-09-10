import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import EmailCompose from './EmailCompose.jsx';
import { professorDetail, matchingResponse, draftResponse, cvVersions, PROF_ID } from '../test/fixtures.js';
import * as matching from '../services/matching.js';
import * as outreach from '../services/outreach.js';
import * as profile from '../services/profile.js';
import * as api from '../services/api.js';
import { useGmailStatus } from '../hooks/useGmailStatus.js';
import { savePendingIntent, getPendingIntent } from '../services/gmail.js';

vi.mock('../services/matching.js', () => ({
  fetchMatches: vi.fn(),
  fetchProfessor: vi.fn(),
  fetchUniversities: vi.fn(),
}));

vi.mock('../services/outreach.js', () => ({
  generateDraft: vi.fn(),
  saveDraft: vi.fn(),
  listCvVersions: vi.fn(),
  attachCv: vi.fn(),
  getSendPreview: vi.fn(),
  sendDraft: vi.fn(),
  getDraft: vi.fn(),
  listHistory: vi.fn(),
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

function renderCompose() {
  return render(
    <MemoryRouter initialEntries={[`/outreach/compose/${PROF_ID}`]}>
      <Routes>
        <Route path="/outreach/compose/:professorId" element={<EmailCompose />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function generateDraftInUi(user) {
  await screen.findByText('Jane Smith');
  await user.click(screen.getByRole('button', { name: /Generate Draft/i }));
  await screen.findByDisplayValue(draftResponse.subject);
}

describe('Email compose page', () => {
  beforeEach(() => {
    api.getProfileId.mockReturnValue('p1');
    profile.fetchProfile.mockResolvedValue({ confirmed: true });
    matching.fetchProfessor.mockResolvedValue(professorDetail);
    matching.fetchMatches.mockResolvedValue(matchingResponse);
    outreach.generateDraft.mockResolvedValue(draftResponse);
    outreach.saveDraft.mockResolvedValue({ draft_id: 'draft-1', status: 'ready', message: 'saved' });
    outreach.listCvVersions.mockResolvedValue(cvVersions);
    outreach.attachCv.mockResolvedValue({ draft_id: 'draft-1', cv_version_id: 'cv-1', display_name: 'Resume.pdf', message: 'ok' });
    outreach.getSendPreview.mockResolvedValue({
      to_address: 'jane@stanford.edu',
      from_address: 'me@gmail.com',
      subject: draftResponse.subject,
      body: draftResponse.body,
      cv_display_name: 'Resume.pdf',
      gmail_account: 'me@gmail.com',
    });
    outreach.sendDraft.mockResolvedValue({ draft_id: 'draft-1', status: 'sent', message: 'sent' });
    useGmailStatus.mockReturnValue({
      status: { connected: true, email: 'me@gmail.com' },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  it('renders professor name and university, not [object Object]', async () => {
    renderCompose();
    expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText(/Stanford University/)).toBeInTheDocument();
    expect(screen.getByText(/Computer Science/)).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });

  it('toggles email type between Research Outreach and Research + Opportunity', async () => {
    const user = userEvent.setup();
    renderCompose();
    await screen.findByText('Jane Smith');
    await user.click(screen.getByRole('button', { name: /Research \+ Opportunity/i }));
    await user.click(screen.getByRole('button', { name: /Generate Draft/i }));
    await waitFor(() => {
      expect(outreach.generateDraft).toHaveBeenCalledWith(PROF_ID, 'research_opportunity', null);
    });
  });

  it('Generate Draft calls the API with the correct payload', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    expect(outreach.generateDraft).toHaveBeenCalledWith(PROF_ID, 'research', null);
  });

  it('renders generated body in an editable textarea and subject in an input', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    const subject = screen.getByDisplayValue(draftResponse.subject);
    const body = screen.getByDisplayValue(/Dear Professor Smith/);
    expect(subject.tagName).toBe('INPUT');
    expect(body.tagName).toBe('TEXTAREA');
  });

  it('subject line is editable', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    const subject = screen.getByDisplayValue(draftResponse.subject);
    await user.clear(subject);
    await user.type(subject, 'Updated subject');
    expect(subject).toHaveValue('Updated subject');
  });

  it('Save Draft sends draft id, subject, body, and status ready', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    await user.click(screen.getByRole('button', { name: /Save Draft/i }));
    await waitFor(() => {
      expect(outreach.saveDraft).toHaveBeenCalledWith(
        'draft-1',
        draftResponse.subject,
        draftResponse.body,
        'ready',
      );
    });
  });

  it('after Save Draft the UI shows ready status', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    await user.click(screen.getByRole('button', { name: /Save Draft/i }));
    expect(await screen.findByText(/ready/i)).toBeInTheDocument();
  });

  it('Preview Email shows the email preview', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    await user.click(screen.getByRole('button', { name: /Preview Email/i }));
    expect(await screen.findByText('Email Preview')).toBeInTheDocument();
    expect(screen.getByText('jane@stanford.edu')).toBeInTheDocument();
    expect(screen.getAllByText('me@gmail.com').length).toBeGreaterThan(0);
  });

  it('Send via Gmail calls the send API', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    await user.click(screen.getByRole('button', { name: /Preview Email/i }));
    await screen.findByText('Email Preview');
    await user.click(screen.getByRole('button', { name: /Send Email/i }));
    await waitFor(() => {
      expect(outreach.sendDraft).toHaveBeenCalledWith('draft-1');
    });
  });

  it('does not show preview-API Gmail error in section 4 when connected === true', async () => {
    outreach.getSendPreview.mockRejectedValue(
      new Error('Gmail is not connected. Connect via /gmail/connect.'),
    );
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    expect(screen.queryByText(/Connect via \/gmail\/connect/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Preview Email/i }));
    expect(await screen.findByText('Email Preview')).toBeInTheDocument();
    expect(screen.queryByText(/Connect via \/gmail\/connect/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send Email/i })).toBeInTheDocument();
  });

  it('fills From from Gmail status when preview omits from_address', async () => {
    outreach.getSendPreview.mockResolvedValue({
      to_address: 'jane@stanford.edu',
      from_address: null,
      subject: draftResponse.subject,
      body: draftResponse.body,
      cv_display_name: 'Resume.pdf',
      gmail_account: null,
    });
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    await user.click(screen.getByRole('button', { name: /Preview Email/i }));
    expect(await screen.findByText('Email Preview')).toBeInTheDocument();
    expect(screen.getAllByText('me@gmail.com').length).toBeGreaterThan(0);
    expect(screen.queryByText('Gmail is not connected')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send Email/i })).toBeInTheDocument();
  });

  it('shows Connect Gmail when Gmail is not connected', async () => {
    useGmailStatus.mockReturnValue({
      status: { connected: false, email: null },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    expect(screen.getAllByText(/Connect Gmail/i).length).toBeGreaterThan(0);
  });

  it('preserves the originating compose path when Connect Gmail is clicked', async () => {
    useGmailStatus.mockReturnValue({
      status: { connected: false, email: null },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);

    const [connectButton] = screen.getAllByRole('button', { name: 'Connect Gmail' });
    await user.click(connectButton);

    expect(getPendingIntent()).toMatchObject({
      professor_id: PROF_ID,
      return_path: `/outreach/compose/${PROF_ID}`,
    });
  });

  it('CV attachment dropdown lists available CVs', async () => {
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    expect(await screen.findByRole('option', { name: /Resume.pdf/ })).toBeInTheDocument();
  });

  it('restores the draft left by GmailConnected instead of showing a blank Generate Draft screen', async () => {
    // Simulates landing back on this page after the Gmail OAuth round-trip:
    // GmailConnected reads the intent to decide where to send the browser,
    // but deliberately does NOT clear it — this page is the one that must
    // consume the draft_id and hydrate the saved draft.
    savePendingIntent(PROF_ID, `/outreach/compose/${PROF_ID}`, 'draft-1');
    outreach.getDraft.mockResolvedValue(draftResponse);

    const generateCallsBefore = outreach.generateDraft.mock.calls.length;
    renderCompose();

    // The draft appears without ever clicking "Generate Draft".
    await screen.findByDisplayValue(draftResponse.subject);
    expect(outreach.getDraft).toHaveBeenCalledWith('draft-1');
    expect(outreach.generateDraft.mock.calls.length).toBe(generateCallsBefore);
    expect(getPendingIntent()).toBeNull();
  });

  it('shows a clear error when draft generation fails', async () => {
    outreach.generateDraft.mockRejectedValue(new Error('email_type must be research or research_opportunity'));
    const user = userEvent.setup();
    renderCompose();
    await screen.findByText('Jane Smith');
    await user.click(screen.getByRole('button', { name: /Generate Draft/i }));
    expect(await screen.findByText(/email_type must be research/i)).toBeInTheDocument();
  });

  describe('profile completeness check', () => {
    it('a genuine confirmed:false response shows the incomplete-profile state', async () => {
      profile.fetchProfile.mockResolvedValue({ confirmed: false });
      renderCompose();
      expect(await screen.findByText('Confirm your profile first')).toBeInTheDocument();
    });

    it('confirmed:true renders the normal compose workspace', async () => {
      profile.fetchProfile.mockResolvedValue({ confirmed: true });
      renderCompose();
      expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
      expect(screen.queryByText('Confirm your profile first')).not.toBeInTheDocument();
    });

    it('a failed /profile request does NOT show the incomplete-profile state', async () => {
      profile.fetchProfile.mockRejectedValue(new Error('Network error'));
      renderCompose();
      expect(await screen.findByText("Couldn't check your profile status")).toBeInTheDocument();
      expect(screen.queryByText('Confirm your profile first')).not.toBeInTheDocument();
    });

    it('an already-completed profile recovers via retry instead of looping', async () => {
      profile.fetchProfile
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ confirmed: true });
      const user = userEvent.setup();
      renderCompose();

      await screen.findByText("Couldn't check your profile status");
      await user.click(screen.getByRole('button', { name: /Try again/i }));

      expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
      expect(screen.queryByText('Confirm your profile first')).not.toBeInTheDocument();
      expect(screen.queryByText("Couldn't check your profile status")).not.toBeInTheDocument();
    });
  });
});
