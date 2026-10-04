import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import AppShell from '../components/AppShell/AppShell.jsx';
import GmailWidget from '../components/GmailWidget/GmailWidget.jsx';
import Modal from '../components/Modal.jsx';
import Spinner from '../components/Spinner.jsx';
import SendCelebration from '../components/SendCelebration/SendCelebration.jsx';
import LoadingState from '../components/LoadingState.jsx';
import ErrorState from '../components/ErrorState.jsx';
import { getProfileId } from '../services/api.js';
import { fetchProfile } from '../services/profile.js';
import { fetchProfessor, fetchMatches } from '../services/matching.js';
import {
  generateDraft, saveDraft, listCvVersions, attachCv,
  getSendPreview, sendDraft, getDraft, listDrafts,
} from '../services/outreach.js';
import { clearPendingIntent, getPendingIntent, gmailConnectUrl, savePendingIntent } from '../services/gmail.js';
import { useGmailStatus } from '../hooks/useGmailStatus.js';
import { supabase } from '../lib/supabase.js';

const EMAIL_TYPES = [
  { value: 'research', label: 'Research Outreach' },
  { value: 'research_opportunity', label: 'Research + Opportunity' },
];

function wordCount(text) {
  if (!text) return 0;
  return text.trim().split(/\s+/).filter(Boolean).length;
}

// Matches the single-bounded-retry pattern already used for the matches
// load on Matches.jsx (MATCHES_RETRY_DELAY_MS): production is a real
// cross-origin request to a Render backend that can cold-start after a
// period of inactivity, so the very first request can fail even though the
// service is healthy and every later request would succeed.
//
// Unlike that existing retry, this one is status-aware: it only retries a
// network-level failure (no `status` — fetch() itself failed) or a 5xx
// response. A 401/403/4xx is a deterministic result — retrying it would
// hide a genuine bug (e.g. a real ownership rejection) rather than recover
// from a transient one, so those are rethrown immediately without retrying.
const PROFILE_CHECK_RETRY_DELAY_MS = 1500;

async function withBoundedRetry(fn, { retries = 1, delayMs = PROFILE_CHECK_RETRY_DELAY_MS } = {}) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (e) {
      lastError = e;
      const status = e?.status;
      const isRetryable = status === undefined || status >= 500;
      if (!isRetryable || attempt === retries) throw e;
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
  throw lastError;
}

const DRAFT_READY_STATUSES = ['ready', 'edited'];

/* ── Step card header ─────────────────────────────────── */
function StepCard({ number, title, done, children }) {
  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--line)',
      borderRadius: 'var(--r-lg)',
      overflow: 'hidden',
      marginBottom: '1rem',
      boxShadow: 'var(--shadow-sm)',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '.65rem',
        padding: '.9rem 1.25rem',
        borderBottom: '1px solid var(--line-light)',
        background: 'var(--bg)',
      }}>
        <div style={{
          width: '24px', height: '24px', borderRadius: '50%',
          background: done ? 'var(--green)' : 'var(--navy)',
          color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '.75rem', fontWeight: 700, flexShrink: 0,
        }}>
          {done
            ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>
            : number
          }
        </div>
        <h2 style={{ fontSize: '.9375rem', fontWeight: 700, color: 'var(--navy)', margin: 0 }}>{title}</h2>
      </div>
      <div style={{ padding: '1.25rem' }}>
        {children}
      </div>
    </div>
  );
}

export default function EmailCompose() {
  const { professorId } = useParams();
  const navigate = useNavigate();
  const profileId = getProfileId();

  const [prof, setProf] = useState(null);
  const [match, setMatch] = useState(null);
  const [profLoading, setProfLoading] = useState(true);
  const [profError, setProfError] = useState(null);

  const [profileConfirmed, setProfileConfirmed] = useState(null);
  const [profileCheckError, setProfileCheckError] = useState(false);

  // Step 1: draft generation
  const [emailType, setEmailType] = useState('research');
  const [generating, setGenerating] = useState(false);
  const [draft, setDraft] = useState(null);
  const [draftSubject, setDraftSubject] = useState('');
  const [draftBody, setDraftBody] = useState('');
  const [unsaved, setUnsaved] = useState(false);
  const [genError, setGenError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  // Step 2: CV attachment
  const [cvVersions, setCvVersions] = useState([]);
  const [selectedCv, setSelectedCv] = useState('');
  const [cvLoading, setCvLoading] = useState(false);
  const [cvAttaching, setCvAttaching] = useState(false);
  const [cvAttached, setCvAttached] = useState(false);
  const [cvAttachError, setCvAttachError] = useState(null);
  const usableCvs = cvVersions.filter(v => v.file_available !== false);

  // Step 4: preview + send
  const [showPreview, setShowPreview] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState(null);
  const [sendError, setSendError] = useState(null);
  const [celebrating, setCelebrating] = useState(false);
  const [userEmail, setUserEmail] = useState(null);

  const { status: gmailStatus, loading: gmailLoading, refetch: refetchGmailStatus } = useGmailStatus();
  const gmailConnected = gmailStatus?.connected === true;
  const isGmailConnected = gmailStatus?.connected === true;

  // Restoring a draft after returning from the Gmail OAuth round-trip
  const [restoring, setRestoring] = useState(false);
  const [restoredNotice, setRestoredNotice] = useState(false);
  const resumedRef = useRef(false);

  // Applies a persisted draft (from either restore path below) to local
  // state. Shared so both paths stay in exact sync with what the backend
  // actually stored — the database record is the source of truth, not
  // whatever React happened to hold before the page was reloaded.
  const applyRestoredDraft = useCallback((data) => {
    setDraft(data);
    setDraftSubject(data.subject || '');
    setDraftBody(data.body || '');
    setEmailType(data.email_type || 'research');
    setUnsaved(false);
    if (data.cv_version_id) {
      setSelectedCv(data.cv_version_id);
      setCvAttached(true);
    }
  }, []);

  // Finds the most recent, not-yet-sent draft for this professor directly
  // from the backend. This is the fallback (and, for a plain page
  // load/refresh, the ONLY) way the compose page recovers existing work —
  // it does not depend on localStorage or any OAuth-specific bookkeeping,
  // because that state can be lost (different tab, cleared storage, OAuth
  // intent referencing a draft that no longer resolves) while the actual
  // draft in the database is still perfectly fine.
  const restoreLatestDraftForProfessor = useCallback(() => {
    return listDrafts()
      .then(drafts => (drafts || []).find(d =>
        String(d.professor_id) === String(professorId) && d.generation_status !== 'sent'
      ))
      .then(data => {
        if (!data) return false;
        applyRestoredDraft(data);
        return true;
      })
      .catch(() => false);
  }, [professorId, applyRestoredDraft]);

  useEffect(() => {
    if (resumedRef.current || !professorId) return;
    resumedRef.current = true;

    const intent = getPendingIntent();
    clearPendingIntent();
    const cameFromOAuth = !!(intent && String(intent.professor_id) === String(professorId) && intent.draft_id);

    if (!cameFromOAuth) {
      // Not returning from Gmail OAuth — still check the database for an
      // existing draft (covers a plain browser refresh or simply
      // revisiting this compose page). No dedicated "restoring" screen for
      // this path: it resolves quickly and silently, exactly as if the
      // state had never left.
      restoreLatestDraftForProfessor();
      return;
    }

    setRestoring(true);
    getDraft(intent.draft_id)
      .then(data => {
        applyRestoredDraft(data);
        setRestoredNotice(true);
      })
      .catch(() =>
        // The specific draft referenced by the OAuth intent couldn't be
        // loaded — fall back to the database lookup rather than leaving
        // the user on a blank compose page for a draft that may still
        // genuinely exist.
        restoreLatestDraftForProfessor().then(found => { if (found) setRestoredNotice(true); })
      )
      .finally(() => setRestoring(false));
  }, [professorId, applyRestoredDraft, restoreLatestDraftForProfessor]);

  // Auto-hide the "restored" banner, but only once it's actually visible
  // (profLoading can outlast the draft fetch, so the countdown must not
  // start until the loading gate that hides the banner has cleared).
  useEffect(() => {
    if (!restoredNotice || profLoading || restoring) return;
    const t = setTimeout(() => setRestoredNotice(false), 5000);
    return () => clearTimeout(t);
  }, [restoredNotice, profLoading, restoring]);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUserEmail(data?.user?.email || null);
    }).catch(() => {});
  }, []);

  const checkProfile = useCallback(() => {
    if (!profileId) return;
    setProfileCheckError(false);
    // A failed /profile request (network, CORS, timeout, cold start, etc.)
    // does NOT mean the profile is incomplete — only an actual `confirmed:
    // false` response does. Track the failure separately so it can't be
    // mistaken for "profile incomplete" and trigger a false onboarding loop.
    // A bounded retry absorbs a single transient failure (e.g. a backend
    // cold start) automatically — the same recovery "Try again" already
    // provided manually — without retrying a genuine 401/403/4xx, which
    // would just hide a real bug instead of fixing one.
    withBoundedRetry(() => fetchProfile())
      .then(p => setProfileConfirmed(p.confirmed))
      .catch(() => setProfileCheckError(true));
  }, [profileId]);

  useEffect(() => { checkProfile(); }, [checkProfile]);

  useEffect(() => {
    if (!professorId) return;
    setProfLoading(true);
    setProfError(null);

    // fetchProfessor is the fast, required lookup for this page's core
    // content. fetchMatches({limit:100}) is only used for the optional
    // "why this match" evidence box below — it re-scores every professor
    // and is measurably slow. Blocking the whole page on it (via
    // Promise.all) made navigating here feel broken: the page would sit on
    // a loading screen for several seconds even though the professor data
    // itself was ready almost immediately, which is what produced the
    // "Prepare Email needs multiple clicks" report — the first click
    // worked, but nothing appeared to happen for seconds afterward.
    fetchProfessor(professorId)
      .then(profData => { if (profData) setProf(profData); })
      .catch(e => setProfError(e.message))
      .finally(() => setProfLoading(false));

    fetchMatches({ limit: 100 })
      .then(d => (d.matches || []).find(m => {
        const p = m.professor || {};
        return String(p.id) === String(professorId) || String(p.professor_id) === String(professorId);
      }))
      .then(matchData => {
        if (matchData) {
          setMatch(matchData);
          setProf(prev => prev || matchData.professor || null);
        }
      })
      .catch(() => {});
  }, [professorId]);

  useEffect(() => {
    if (!draft?.draft_id) return;
    setCvLoading(true);
    listCvVersions()
      .then(data => {
        const all = data || [];
        setCvVersions(all);
        // Only CVs whose file is actually stored can be attached.
        const usable = all.filter(v => v.file_available !== false);
        // The CV already attached to this draft (server-side truth) always
        // wins over guessing the account's default CV — restoring a draft
        // must never silently swap the selection back to something the
        // user didn't choose for this specific outreach email.
        if (draft.cv_version_id && usable.some(v => v.cv_version_id === draft.cv_version_id)) {
          setSelectedCv(draft.cv_version_id);
          setCvAttached(true);
        } else {
          const def = usable.find(v => v.is_default) || usable[0];
          setSelectedCv(def ? def.cv_version_id : '');
          setCvAttached(false);
        }
      })
      .catch(() => {})
      .finally(() => setCvLoading(false));
  }, [draft?.draft_id, draft?.cv_version_id]);

  const handleGenerate = async () => {
    if (!profileId || !professorId) return;
    setGenerating(true);
    setGenError(null);
    try {
      const data = await generateDraft(professorId, emailType, null);
      setDraft(data);
      setDraftSubject(data.subject || '');
      setDraftBody(data.body || '');
      setUnsaved(false);
    } catch (e) {
      setGenError(e.message || 'Generation failed. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!draft?.draft_id) return;
    setSaving(true);
    try {
      const saved = await saveDraft(draft.draft_id, draftSubject, draftBody, 'ready');
      setDraft(prev => prev ? { ...prev, status: saved?.status || 'ready', generation_status: saved?.status || 'ready' } : prev);
      setUnsaved(false);
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2200);
    } catch (e) {
      setGenError(e.message || 'Could not save draft.');
    } finally {
      setSaving(false);
    }
  };

  // Auto-save any unsaved edits before leaving the app for the Gmail OAuth
  // round-trip, so nothing is lost even if the user never clicked Save.
  const saveBeforeGmailRedirect = async () => {
    if (!draft?.draft_id || !unsaved) return;
    try {
      await saveDraft(draft.draft_id, draftSubject, draftBody, 'ready');
      setUnsaved(false);
    } catch {
      // best-effort — the draft is still safely stored from the last generate/save
    }
  };

  const handleAttachCv = async () => {
    if (!draft?.draft_id || !selectedCv) return;
    setCvAttaching(true);
    setCvAttachError(null);
    try {
      await attachCv(draft.draft_id, selectedCv);
      setCvAttached(true);
      // Keep local draft state in sync with what the backend now has, so
      // any later re-render (or the CV-versions effect above) sees the
      // real attached CV rather than a stale/undefined value.
      setDraft(prev => prev ? { ...prev, cv_version_id: selectedCv } : prev);
    } catch (e) {
      // Previously silently ignored — a failure (e.g. the stored CV file
      // being unavailable) left the button just reverting to "Attach CV"
      // with zero feedback, which is what made this "sometimes fail" for
      // no apparent reason. Surface it so the user knows to retry or
      // re-upload instead of assuming the app is just flaky.
      setCvAttachError(e.message || 'Could not attach this CV. Please try again.');
    } finally {
      setCvAttaching(false);
    }
  };

  const handlePreview = async () => {
    if (!draft?.draft_id) return;
    if (gmailStatus?.connected !== true) return;
    setPreviewLoading(true);
    setSendError(null);
    setPreviewError(null);
    const localPreview = {
      to_address: prof?.email || '',
      from_address: gmailStatus?.email || userEmail || null,
      subject: draftSubject,
      body: draftBody,
      cv_display_name: cvVersions.find(v => v.cv_version_id === selectedCv)?.display_name || null,
      gmail_account: gmailStatus?.email || userEmail || null,
    };
    try {
      // The backend only allows preview/send for a draft saved as "ready"
      // (or "edited") — the single lifecycle is generate -> save -> ready
      // -> preview -> send. Previously, a preview request for a
      // still-"generated" (never explicitly saved) draft failed on the
      // backend, and that failure was silently swallowed below, showing a
      // preview built from local state anyway — so Preview looked fine but
      // the identical validation then failed Send with "Draft status is
      // 'generated'. Save as 'ready' before sending." Save first so
      // Preview and Send always agree, with no extra click required.
      const currentStatus = draft.status || draft.generation_status;
      if (unsaved || !DRAFT_READY_STATUSES.includes(currentStatus)) {
        const saved = await saveDraft(draft.draft_id, draftSubject, draftBody, 'ready');
        setDraft(prev => prev ? { ...prev, status: saved?.status || 'ready', generation_status: saved?.status || 'ready' } : prev);
        setUnsaved(false);
      }
      const data = await getSendPreview(draft.draft_id);
      setPreview({
        ...localPreview,
        ...data,
        from_address: data?.from_address || localPreview.from_address,
        gmail_account: data?.gmail_account || localPreview.gmail_account,
      });
      setShowPreview(true);
    } catch (e) {
      // A real backend validation failure must be surfaced, not hidden
      // behind a client-reconstructed preview that Send would then fail
      // on anyway — that "fake success" is exactly what produced the
      // confusing preview-looks-fine-but-send-fails experience.
      setPreviewError(e.message || 'Could not load preview. Please try again.');
    }
    setPreviewLoading(false);
  };

  const [connectingGmail, setConnectingGmail] = useState(false);

  const handleConnectGmail = async () => {
    if (!profileId) return;
    setConnectingGmail(true);
    await saveBeforeGmailRedirect();
    const returnPath = `/outreach/compose/${professorId}`;
    savePendingIntent(professorId, returnPath, draft?.draft_id || null);
    window.location.href = gmailConnectUrl(profileId, returnPath);
  };

  const handleSend = async () => {
    if (!draft?.draft_id) return;
    setSending(true);
    setSendError(null);
    try {
      const result = await sendDraft(draft.draft_id);
      setSendResult(result);
      setShowPreview(false);
      setCelebrating(true);
    } catch (e) {
      setSendError(e.message || 'Send failed.');
      // A 401 means the Gmail connection can't be used: refresh its status so
      // the page switches to "Reconnect Gmail" instead of a dead Send button.
      if (e.status === 401) refetchGmailStatus?.();
    } finally {
      setSending(false);
    }
  };

  const profName = prof
    ? [prof.first_name, prof.last_name].filter(Boolean).join(' ') || prof.name || 'Professor'
    : '…';
  const profDeptUniv = [prof?.department?.name, prof?.university?.name].filter(Boolean).join(', ');
  // Many directory listings publish no email. Say so up front instead of
  // letting the student write, attach and only then fail at preview.
  const noProfessorEmail = Boolean(prof) && !prof.email;
  const profWebsite = prof?.website_url || prof?.website || prof?.source_url || '';
  const [copied, setCopied] = useState(false);
  const handleCopyEmail = async () => {
    const text = `Subject: ${draftSubject || draft?.subject || ''}\n\n${draftBody || draft?.body || ''}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  };
  const fromAddress = preview?.from_address
    || preview?.gmail_account
    || gmailStatus?.email
    || userEmail
    || (gmailConnected ? 'Connected Gmail account' : null);

  if (!profileId) {
    return (
      <AppShell>
        <ErrorState title="Profile required" message="Please set up your profile before composing outreach emails." />
      </AppShell>
    );
  }

  if (profileConfirmed === false) {
    return (
      <AppShell>
        <div style={{ maxWidth: '540px', margin: '3rem auto', padding: '0 1.5rem', textAlign: 'center' }}>
          <div style={{
            background: 'var(--card)', border: '1px solid var(--line)',
            borderRadius: 'var(--r-lg)', padding: '2rem', boxShadow: 'var(--shadow-sm)',
          }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '.5rem' }}>Confirm your profile first</h2>
            <p style={{ color: 'var(--muted)', fontSize: '.875rem', marginBottom: '1.25rem' }}>
              Complete your profile setup to compose personalized outreach emails.
            </p>
            <Link to="/onboarding" style={{
              display: 'inline-block',
              background: 'var(--navy)', color: '#fff',
              padding: '.65rem 1.25rem',
              borderRadius: 'var(--r-md)', textDecoration: 'none',
              fontWeight: 600, fontSize: '.875rem',
            }}>
              Complete profile setup
            </Link>
          </div>
        </div>
      </AppShell>
    );
  }

  // Only reached when /profile has never successfully responded AND the
  // last attempt failed — distinct from profileConfirmed === false above,
  // which requires an actual server response. Retrying re-runs the same
  // check without assuming the profile is incomplete.
  if (profileConfirmed === null && profileCheckError) {
    return (
      <AppShell>
        <ErrorState
          title="Couldn't check your profile status"
          message="This is usually a temporary connection issue; your profile itself hasn't changed."
          onRetry={checkProfile}
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      {/* ── Professor context header (dark navy bar) ── */}
      <div style={{
        background: 'var(--navy)',
        padding: '.85rem 1.5rem',
        borderBottom: '1px solid rgba(255,255,255,.08)',
      }}>
        <div style={{
          maxWidth: '720px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
        }}>
          <div>
            <div style={{ fontSize: '.7rem', color: 'rgba(255,255,255,.4)', fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', marginBottom: '.2rem' }}>
              Academic Outreach Workspace
            </div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '1.0625rem', fontWeight: 700, color: '#fff' }}>
              {profLoading ? '…' : profName}
            </div>
            {profDeptUniv && (
              <div style={{ fontSize: '.8rem', color: 'rgba(255,255,255,.5)', marginTop: '.1rem' }}>{profDeptUniv}</div>
            )}
          </div>
          <GmailWidget
            professorId={professorId}
            returnPath={`/outreach/compose/${professorId}`}
            draftId={draft?.draft_id}
            onBeforeConnect={saveBeforeGmailRedirect}
            compact
          />
        </div>
      </div>

      <div style={{ minHeight: 'calc(100vh - var(--nav-h) - 72px)', background: 'var(--bg)', padding: '1.75rem 1.5rem' }}>
        <div style={{ maxWidth: '720px', margin: '0 auto' }}>
          {(profLoading || restoring) && (
            <LoadingState message={restoring ? 'Restoring your draft…' : 'Loading professor information…'} />
          )}
          {profError && <ErrorState title="Could not load professor" message={profError} />}

          {!profLoading && !restoring && (
            <>
              {noProfessorEmail && !sendResult && (
                <div className="banner banner-warning" role="status" style={{ marginBottom: '1rem', display: 'block' }}>
                  <strong>No email address is listed for {profName}.</strong>{' '}
                  You can still write and personalise this email, then copy it and contact them through
                  {profWebsite ? (
                    <> their <a href={profWebsite} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600 }}>faculty page</a></>
                  ) : ' their university faculty page'}. Sending through Gmail needs a verified address, so it is turned off for this professor.
                </div>
              )}
              {restoredNotice && (
                <div className="banner banner-success" style={{ marginBottom: '1rem' }}>
                  <span>✓ Welcome back, your draft was restored right where you left off.</span>
                </div>
              )}

              {celebrating && sendResult && (
                <SendCelebration
                  professorName={profName}
                  toAddress={preview?.to_address || prof?.email}
                  cvName={preview?.cv_display_name}
                  sentAt={sendResult.sent_at}
                  onClose={() => setCelebrating(false)}
                />
              )}

              {/* ── Sent success ─────────────────────── */}
              {sendResult && (
                <div style={{
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-lg)',
                  padding: '2rem',
                  textAlign: 'center',
                  marginBottom: '1rem',
                  boxShadow: 'var(--shadow-sm)',
                }}>
                  <div style={{
                    width: '56px', height: '56px', borderRadius: '50%',
                    background: 'var(--green-bg)', border: '2px solid var(--green-bdr)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem',
                  }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2.5"><path d="M20 6L9 17l-5-5"/></svg>
                  </div>
                  <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '.4rem', fontFamily: 'var(--font-serif)' }}>Email sent successfully</h2>
                  <p style={{ color: 'var(--muted)', fontSize: '.875rem', marginBottom: '1.25rem' }}>
                    Your email to {profName} has been sent successfully.
                  </p>
                  <Link to="/outreach/history" style={{
                    display: 'inline-flex', alignItems: 'center', gap: '.3rem',
                    padding: '.5rem 1rem',
                    background: 'var(--card)', color: 'var(--ink)',
                    border: '1px solid var(--line)', borderRadius: 'var(--r-md)',
                    textDecoration: 'none', fontSize: '.875rem', fontWeight: 500,
                  }}>
                    View in Outreach History
                  </Link>
                </div>
              )}

              {/* ── Step 1: Email type + generation ────── */}
              <StepCard number="1" title="Email type" done={false}>
                {/* Pill toggle */}
                <div style={{
                  display: 'inline-flex',
                  background: 'var(--line-light)',
                  borderRadius: 'var(--r-md)',
                  padding: '.2rem',
                  marginBottom: '1.1rem',
                }}>
                  {EMAIL_TYPES.map(et => (
                    <button
                      key={et.value}
                      onClick={() => setEmailType(et.value)}
                      style={{
                        padding: '.4rem .95rem',
                        borderRadius: 'var(--r-sm)',
                        fontSize: '.875rem',
                        fontWeight: emailType === et.value ? 600 : 500,
                        background: emailType === et.value ? 'var(--card)' : 'transparent',
                        color: emailType === et.value ? 'var(--navy)' : 'var(--muted)',
                        border: emailType === et.value ? '1px solid var(--line)' : '1px solid transparent',
                        cursor: 'pointer',
                        boxShadow: emailType === et.value ? 'var(--shadow-sm)' : 'none',
                        transition: 'all .12s',
                      }}
                    >
                      {et.label}
                    </button>
                  ))}
                </div>

                {/* Match evidence */}
                {match?.research_match?.evidence?.length > 0 && (
                  <div style={{ marginBottom: '1rem', padding: '.8rem 1rem', background: 'var(--accent-bg)', borderRadius: 'var(--r-md)', border: '1px solid var(--accent-bdr)', fontSize: '.8125rem', color: 'var(--ink-2)' }}>
                    <div style={{ fontWeight: 600, marginBottom: '.4rem', color: 'var(--accent)' }}>Research alignment signals</div>
                    {match.research_match.evidence.slice(0, 3).map((e, i) => (
                      <div key={i} style={{ marginBottom: '.2rem' }}>• {e.area || e.description || JSON.stringify(e)}</div>
                    ))}
                  </div>
                )}

                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '.5rem',
                    padding: '.6rem 1.25rem',
                    background: 'var(--navy)', color: '#fff',
                    border: 'none', borderRadius: 'var(--r-md)',
                    fontSize: '.875rem', fontWeight: 600,
                    cursor: generating ? 'not-allowed' : 'pointer',
                    opacity: generating ? .7 : 1,
                  }}
                >
                  {generating ? <><Spinner size={15} color="#fff" /> Generating draft…</> : draft ? 'Regenerate' : 'Generate Draft'}
                </button>

                {genError && (
                  <div className="banner banner-error" style={{ marginTop: '.75rem' }}>
                    {genError}
                  </div>
                )}

                {/* Draft editor */}
                {draft && (
                  <div style={{ marginTop: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '.4rem' }}>
                      <label className="form-label">Subject</label>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
                        {(draft.status || draft.generation_status) && (
                          <span data-testid="draft-status" style={{
                            fontSize: '.72rem', fontWeight: 600, padding: '.15rem .5rem',
                            borderRadius: 'var(--r-xs)',
                            background: (draft.status || draft.generation_status) === 'ready' ? 'var(--accent-bg)' : 'var(--line-light)',
                            color: (draft.status || draft.generation_status) === 'ready' ? 'var(--accent)' : 'var(--muted)',
                            border: `1px solid ${(draft.status || draft.generation_status) === 'ready' ? 'var(--accent-bdr)' : 'var(--line)'}`,
                          }}>
                            {(draft.status || draft.generation_status) === 'ready' ? 'Ready' : (draft.status || draft.generation_status)}
                          </span>
                        )}
                        {unsaved && (
                          <span style={{ fontSize: '.72rem', color: 'var(--amber)', fontWeight: 600, padding: '.15rem .5rem', background: 'var(--amber-bg)', border: '1px solid var(--amber-bdr)', borderRadius: 'var(--r-xs)' }}>
                            Unsaved changes
                          </span>
                        )}
                      </span>
                    </div>
                    <input
                      className="form-input"
                      value={draftSubject}
                      onChange={e => { setDraftSubject(e.target.value); setUnsaved(true); }}
                      placeholder="Email subject"
                      style={{ marginBottom: '.9rem' }}
                    />

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '.4rem' }}>
                      <label className="form-label">Body</label>
                      <span style={{ fontSize: '.75rem', color: 'var(--muted)' }}>{wordCount(draftBody)} words</span>
                    </div>
                    <textarea
                      className="form-textarea"
                      value={draftBody}
                      onChange={e => { setDraftBody(e.target.value); setUnsaved(true); }}
                      rows={14}
                      style={{ fontSize: '.875rem', lineHeight: 1.7 }}
                    />

                    <div style={{ display: 'flex', gap: '.65rem', marginTop: '.75rem', alignItems: 'center' }}>
                      <button
                        onClick={handleSave}
                        disabled={saving}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '.4rem',
                          padding: '.45rem .95rem',
                          background: justSaved ? 'var(--green)' : unsaved ? 'var(--navy)' : 'var(--card)',
                          color: justSaved || unsaved ? '#fff' : 'var(--ink)',
                          border: `1px solid ${justSaved ? 'var(--green)' : unsaved ? 'var(--navy)' : 'var(--line)'}`,
                          borderRadius: 'var(--r-sm)',
                          fontSize: '.8125rem', fontWeight: 600,
                          cursor: saving ? 'not-allowed' : 'pointer',
                          opacity: saving ? .7 : 1,
                          transition: 'background .2s, border-color .2s, color .2s',
                          minWidth: '108px',
                          justifyContent: 'center',
                        }}
                      >
                        {saving
                          ? <><Spinner size={13} color={unsaved ? '#fff' : 'var(--ink)'} /> Saving…</>
                          : justSaved
                            ? <><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5" /></svg> Saved</>
                            : 'Save Draft'}
                      </button>
                      <button
                        onClick={handleGenerate}
                        disabled={generating}
                        style={{
                          padding: '.4rem .85rem',
                          background: 'transparent', color: 'var(--muted)',
                          border: 'none', borderRadius: 'var(--r-sm)',
                          fontSize: '.8125rem', fontWeight: 500,
                          cursor: 'pointer',
                        }}
                      >
                        Regenerate
                      </button>
                    </div>
                  </div>
                )}
              </StepCard>

              {/* ── Step 2: CV attachment ────────────── */}
              {draft && (
                <StepCard number="2" title="Attach CV" done={cvAttached}>
                  {cvLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontSize: '.875rem', color: 'var(--muted)' }}>
                      <Spinner size={14} /> Loading CV versions…
                    </div>
                  ) : usableCvs.length === 0 ? (
                    <div className="banner banner-warning" style={{ margin: 0 }}>
                      {cvVersions.length === 0
                        ? 'You have not uploaded a CV yet.'
                        : 'Your saved CV files are no longer stored on the server.'}{' '}
                      <Link to="/onboarding" style={{ fontWeight: 600 }}>Upload your CV on the My CV page</Link>, then come back to attach it.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '.65rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <select
                        className="form-select"
                        value={selectedCv}
                        onChange={e => { setSelectedCv(e.target.value); setCvAttachError(null); }}
                        style={{ flex: '1 0 200px' }}
                      >
                        <option value="">Select a CV…</option>
                        {usableCvs.map(v => (
                          <option key={v.cv_version_id} value={v.cv_version_id}>
                            {v.display_name}{v.is_default ? ' (active)' : ''}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={handleAttachCv}
                        disabled={cvAttaching || !selectedCv}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '.35rem',
                          padding: '.45rem .9rem',
                          background: cvAttached ? 'var(--green-bg)' : 'var(--card)',
                          color: cvAttached ? 'var(--green)' : 'var(--ink)',
                          border: `1px solid ${cvAttached ? 'var(--green-bdr)' : 'var(--line)'}`,
                          borderRadius: 'var(--r-sm)',
                          fontSize: '.8125rem', fontWeight: 500,
                          cursor: cvAttaching || !selectedCv ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {cvAttaching ? <><Spinner size={13} /> Attaching…</> : cvAttached ? '✓ Attached' : 'Attach CV'}
                      </button>
                      {cvAttachError && (
                        <div className="banner banner-error" style={{ width: '100%', marginTop: '.4rem' }}>
                          {cvAttachError}
                        </div>
                      )}
                    </div>
                  )}
                </StepCard>
              )}

              {/* ── Step 3: Gmail connection ──────────── */}
              {draft && (
                <StepCard number="3" title="Gmail connection" done={isGmailConnected}>
                  <GmailWidget
                    professorId={professorId}
                    returnPath={`/outreach/compose/${professorId}`}
                    draftId={draft?.draft_id}
                    onBeforeConnect={saveBeforeGmailRedirect}
                  />
                </StepCard>
              )}

              {/* ── Step 4: Preview & Send ────────────── */}
              {draft && (
                <StepCard number="4" title={noProfessorEmail ? 'Copy & Send Yourself' : 'Preview & Send'} done={false}>
                  {noProfessorEmail ? (
                    <>
                      <button
                        type="button"
                        onClick={handleCopyEmail}
                        style={{
                          width: '100%',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '.5rem',
                          padding: '.75rem',
                          background: 'var(--navy)', color: '#fff',
                          border: 'none', borderRadius: 'var(--r-md)',
                          fontSize: '.9375rem', fontWeight: 700, cursor: 'pointer',
                        }}
                      >
                        {copied ? '✓ Copied to clipboard' : 'Copy email (subject and body)'}
                      </button>
                      <p style={{ color: 'var(--muted)', fontSize: '.8125rem', margin: '.6rem 0 0', lineHeight: 1.5 }}>
                        Find the professor's address on their {profWebsite
                          ? <a href={profWebsite} target="_blank" rel="noopener noreferrer">faculty page</a>
                          : 'faculty page'}, then paste this into a new email and attach your CV.
                      </p>
                    </>
                  ) : isGmailConnected ? (
                    <>
                      <button
                        onClick={handlePreview}
                        disabled={previewLoading}
                        style={{
                          width: '100%',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '.5rem',
                          padding: '.75rem',
                          background: 'var(--navy)', color: '#fff',
                          border: 'none', borderRadius: 'var(--r-md)',
                          fontSize: '.9375rem', fontWeight: 700,
                          cursor: previewLoading ? 'not-allowed' : 'pointer',
                          opacity: previewLoading ? .7 : 1,
                        }}
                      >
                        {previewLoading ? <><Spinner size={15} color="#fff" /> Loading preview…</> : 'Preview Email'}
                      </button>
                      {previewError && (
                        <div className="banner banner-error" style={{ marginTop: '.75rem' }}>
                          {previewError}
                        </div>
                      )}
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={handleConnectGmail}
                      disabled={connectingGmail}
                      style={{
                        width: '100%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '.5rem',
                        padding: '.75rem',
                        background: 'var(--navy)', color: '#fff',
                        border: 'none', borderRadius: 'var(--r-md)',
                        fontSize: '.9375rem', fontWeight: 700,
                        cursor: connectingGmail ? 'not-allowed' : 'pointer',
                        opacity: connectingGmail ? .7 : 1,
                      }}
                    >
                      {connectingGmail ? <><Spinner size={15} color="#fff" /> Connecting…</> : 'Connect Gmail'}
                    </button>
                  )}
                </StepCard>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Preview modal ─────────────────────────────── */}
      <Modal isOpen={showPreview} onClose={() => setShowPreview(false)} title="Email Preview" maxWidth="600px">
        {preview && (
          <div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '.65rem', marginBottom: '1.25rem' }}>
              {[
                ['To', preview.to_address],
                ['From', fromAddress],
                ['Subject', preview.subject],
                ['CV', preview.cv_display_name || '(none)'],
                ['Sending via', fromAddress],
              ].map(([label, value]) => (
                <div key={label} style={{ display: 'flex', gap: '.75rem', fontSize: '.875rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--ink-2)', width: '80px', flexShrink: 0 }}>{label}</span>
                  <span style={{ color: 'var(--ink)' }}>{value || '—'}</span>
                </div>
              ))}
              <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontSize: '.8125rem', marginTop: '.15rem' }}>
                <span className={`status-dot ${gmailConnected ? 'green' : 'grey'}`} />
                <span style={{ color: gmailConnected ? 'var(--green)' : 'var(--muted)', fontWeight: 500 }}>
                  {gmailLoading
                    ? 'Checking Gmail…'
                    : gmailConnected
                      ? (gmailStatus?.email || userEmail || 'Gmail connected')
                      : 'Gmail is not connected'}
                </span>
              </div>
            </div>

            <div style={{ height: '1px', background: 'var(--line)', marginBottom: '1rem' }} />

            <div style={{
              fontSize: '.875rem',
              color: 'var(--ink)',
              lineHeight: 1.75,
              background: 'var(--bg)',
              borderRadius: 'var(--r-md)',
              padding: '1rem',
              whiteSpace: 'pre-wrap',
              maxHeight: '300px',
              overflow: 'auto',
            }}>
              {preview.body}
            </div>

            {sendError && !/gmail is not connected/i.test(sendError) && (
              <div className="banner banner-error" style={{ marginTop: '1rem' }}>
                {sendError}
              </div>
            )}

            <div style={{ display: 'flex', gap: '.65rem', marginTop: '1.25rem' }}>
              <button onClick={() => setShowPreview(false)} style={{
                padding: '.65rem 1.25rem',
                background: 'var(--card)', color: 'var(--ink)',
                border: '1px solid var(--line)', borderRadius: 'var(--r-md)',
                fontSize: '.875rem', fontWeight: 500, cursor: 'pointer',
              }}>
                Edit draft
              </button>
              {gmailConnected ? (
                <button
                  onClick={handleSend}
                  disabled={sending || gmailLoading}
                  style={{
                    flex: 1,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '.5rem',
                    padding: '.65rem 1rem',
                    background: 'var(--navy)', color: '#fff',
                    border: 'none', borderRadius: 'var(--r-md)',
                    fontSize: '.9375rem', fontWeight: 700,
                    cursor: sending ? 'not-allowed' : 'pointer',
                    opacity: sending ? .7 : 1,
                  }}
                >
                  {sending ? <><Spinner size={15} color="#fff" /> Sending…</> : 'Send Email'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowPreview(false)}
                  style={{
                    flex: 1,
                    padding: '.65rem 1rem',
                    background: 'var(--navy)', color: '#fff',
                    border: 'none', borderRadius: 'var(--r-md)',
                    fontSize: '.9375rem', fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Connect Gmail to Send
                </button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </AppShell>
  );
}
