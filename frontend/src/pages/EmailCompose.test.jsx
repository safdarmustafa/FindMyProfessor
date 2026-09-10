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
  listDrafts: vi.fn(),
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
    // Reset first: a test that queues a sequence of mockRejectedValueOnce/
    // mockResolvedValueOnce (e.g. the profile-check retry tests below)
    // must not leak leftover queued results into the next test.
    profile.fetchProfile.mockReset();
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
    outreach.listDrafts.mockResolvedValue([]);
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

  it('renders professor info and lets the user start composing without waiting for the slow matches re-scan', async () => {
    // fetchMatches({limit:100}) re-scores every professor just to find this
    // one's match evidence — it must never block Generate Draft, which only
    // needs the fast, targeted fetchProfessor call. Blocking the whole page
    // on it produced the "Prepare Email needs multiple clicks" report: the
    // click worked, but this page then sat blank for several seconds.
    matching.fetchMatches.mockReturnValue(new Promise(() => {})); // never resolves
    renderCompose();
    expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Generate Draft/i })).toBeInTheDocument();
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

  it('surfaces a real preview failure instead of faking success with local data', async () => {
    // Previously any getSendPreview() failure was swallowed and the modal
    // opened anyway using client-reconstructed data — which is exactly
    // what let a draft that the backend would refuse to send (e.g. still
    // "generated", not "ready") look sendable in Preview, only to fail at
    // Send with a confusing error. A genuine preview failure must be shown,
    // not hidden, and the modal must not open on top of it.
    outreach.getSendPreview.mockRejectedValue(
      new Error('Gmail is not connected. Connect via /gmail/connect.'),
    );
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    await user.click(screen.getByRole('button', { name: /Preview Email/i }));
    expect(await screen.findByText(/Connect via \/gmail\/connect/i)).toBeInTheDocument();
    expect(screen.queryByText('Email Preview')).not.toBeInTheDocument();
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

  it('shows a clear error instead of silently failing when CV attachment fails', async () => {
    // Previously a failed attachCv() (e.g. the stored file being
    // unavailable) was swallowed entirely — the button just reset with no
    // feedback, which is what made attachment look like it "randomly
    // failed" with no explanation.
    outreach.attachCv.mockRejectedValue(new Error('CV file is not available.'));
    const user = userEvent.setup();
    renderCompose();
    await generateDraftInUi(user);
    await screen.findByRole('option', { name: /Resume.pdf/ });

    await user.selectOptions(screen.getByRole('combobox'), 'cv-1');
    await user.click(screen.getByRole('button', { name: /Attach CV/i }));

    expect(await screen.findByText('CV file is not available.')).toBeInTheDocument();
    expect(screen.queryByText('✓ Attached')).not.toBeInTheDocument();
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

  it('restores CV selection and email type, not just subject/body, after Gmail OAuth', async () => {
    // Bug 3: the generated draft — including which CV was attached and
    // which email type was chosen — must survive the round trip intact,
    // not just the subject/body text.
    savePendingIntent(PROF_ID, `/outreach/compose/${PROF_ID}`, 'draft-cv-1');
    outreach.getDraft.mockResolvedValue({
      ...draftResponse,
      draft_id: 'draft-cv-1',
      email_type: 'research_opportunity',
      cv_version_id: 'cv-1',
    });

    renderCompose();

    await screen.findByDisplayValue(draftResponse.subject);
    expect(outreach.getDraft).toHaveBeenCalledWith('draft-cv-1');
    expect(await screen.findByText('✓ Attached')).toBeInTheDocument();
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
      // Persistent failure: both the initial attempt and the one bounded
      // automatic retry fail, so the error state is genuinely reached.
      profile.fetchProfile.mockRejectedValue(new Error('Network error'));
      renderCompose();
      expect(await screen.findByText("Couldn't check your profile status", {}, { timeout: 4000 })).toBeInTheDocument();
      expect(screen.queryByText('Confirm your profile first')).not.toBeInTheDocument();
    });

    it('a single transient /profile failure self-heals via the automatic retry — no error shown, no click needed', async () => {
      // Production is a real cross-origin request to a Render backend that
      // can cold-start after a period of inactivity — the very first
      // request can fail even though the service is healthy and every
      // later request would succeed. This must recover on its own, the
      // same way Matches.jsx's matches load already does, instead of
      // showing "Couldn't check your profile status" for a blip that
      // resolves itself a moment later.
      profile.fetchProfile
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ confirmed: true });
      renderCompose();

      // "Jane Smith" alone isn't proof the retry ran — professor info
      // renders immediately regardless of profile-check state (see "renders
      // professor info ... without waiting for the slow matches re-scan"
      // above). Only the call count proves the retry genuinely completed;
      // waiting for it here also avoids leaving a dangling retry timer that
      // would otherwise fire mid-way through a *later* test and pollute it.
      await waitFor(() => {
        expect(profile.fetchProfile).toHaveBeenCalledTimes(2);
      }, { timeout: 4000 });

      expect(screen.queryByText("Couldn't check your profile status")).not.toBeInTheDocument();
      expect(screen.queryByText('Confirm your profile first')).not.toBeInTheDocument();
    });

    it('shows an error state only after both the initial attempt and the automatic retry fail, then recovers via manual Try again', async () => {
      profile.fetchProfile
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ confirmed: true });
      const user = userEvent.setup();
      renderCompose();

      await screen.findByText("Couldn't check your profile status", {}, { timeout: 4000 });
      await user.click(screen.getByRole('button', { name: /Try again/i }));

      await waitFor(() => {
        expect(profile.fetchProfile).toHaveBeenCalledTimes(3);
      }, { timeout: 4000 });
      expect(screen.queryByText('Confirm your profile first')).not.toBeInTheDocument();
      expect(screen.queryByText("Couldn't check your profile status")).not.toBeInTheDocument();
    });

    it('does NOT retry a deterministic 403 (ownership rejection) — that would hide a real bug', async () => {
      const err = new Error('X-Profile-Id does not match the authenticated account.');
      err.status = 403;
      profile.fetchProfile.mockRejectedValue(err);
      renderCompose();

      expect(await screen.findByText("Couldn't check your profile status")).toBeInTheDocument();
      // A 403 is deterministic — retrying it would just fail again and
      // waste the retry delay, so it must be called exactly once.
      expect(profile.fetchProfile).toHaveBeenCalledTimes(1);
    });
  });
});
