import React from 'react';
import { useGmailStatus } from '../../hooks/useGmailStatus.js';
import { disconnectGmail, gmailConnectUrl, savePendingIntent } from '../../services/gmail.js';
import { getProfileId } from '../../services/api.js';
import Spinner from '../Spinner.jsx';

export default function GmailWidget({ professorId, returnPath, draftId, onBeforeConnect, onStatusChange, compact = false }) {
  const { status, loading, refetch } = useGmailStatus();
  const [disconnecting, setDisconnecting] = React.useState(false);
  const [connecting, setConnecting] = React.useState(false);
  const [disconnectError, setDisconnectError] = React.useState(null);

  const handleConnect = async () => {
    const profileId = getProfileId();
    if (!profileId) return;
    setConnecting(true);
    if (onBeforeConnect) {
      try { await onBeforeConnect(); } catch {}
    }
    if (professorId && returnPath) {
      savePendingIntent(professorId, returnPath, draftId);
    }
    window.location.href = gmailConnectUrl(profileId, returnPath);
  };

  const handleDisconnect = async () => {
    setDisconnecting(true);
    setDisconnectError(null);
    try {
      await disconnectGmail();
      await refetch();
      if (onStatusChange) onStatusChange(false);
    } catch (e) {
      // Previously silently ignored — a failed disconnect just reverted the
      // button with no feedback, leaving the user unsure whether Gmail was
      // actually disconnected or not.
      setDisconnectError(e.message || 'Could not disconnect Gmail. Please try again.');
    } finally {
      setDisconnecting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontSize: '.8125rem', color: 'var(--muted)' }}>
        <Spinner size={14} />
        <span>Checking Gmail…</span>
      </div>
    );
  }

  // CRITICAL: connected === true means Gmail is connected even if email === null
  const isConnected = status?.connected === true;

  if (isConnected) {
    const label = status.email ? status.email : 'Gmail connected';
    if (compact) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontSize: '.8125rem' }}>
          <span className="status-dot green" />
          <span style={{ color: 'rgba(255,255,255,.8)' }}>{label}</span>
        </div>
      );
    }
    return (
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '.75rem',
          padding: '.65rem 1rem',
          background: 'var(--green-bg)',
          border: '1px solid var(--green-bdr)',
          borderRadius: 'var(--r-md)',
          fontSize: '.875rem',
        }}>
          <span className="status-dot green" />
          <span style={{ color: 'var(--green)', flex: 1, fontWeight: 500 }}>{label}</span>
          <button
            onClick={handleDisconnect}
            disabled={disconnecting}
            className="btn btn-sm"
            style={{ background: 'none', border: '1px solid var(--green-bdr)', color: 'var(--green)', padding: '.2rem .6rem', fontSize: '.75rem' }}
          >
            {disconnecting ? 'Disconnecting…' : 'Disconnect'}
          </button>
        </div>
        {disconnectError && (
          <div className="banner banner-error" style={{ marginTop: '.5rem' }}>
            {disconnectError}
          </div>
        )}
      </div>
    );
  }

  if (compact) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontSize: '.8125rem' }}>
        <span className="status-dot grey" />
        <button
          onClick={handleConnect}
          disabled={connecting}
          style={{ background: 'none', border: 'none', cursor: connecting ? 'not-allowed' : 'pointer', color: 'rgba(255,255,255,.7)', fontSize: '.8125rem', padding: 0, textDecoration: 'underline' }}
        >
          {connecting ? 'Connecting…' : 'Connect Gmail'}
        </button>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '.75rem',
      padding: '.65rem 1rem',
      background: 'var(--line-light)',
      border: '1px solid var(--line)',
      borderRadius: 'var(--r-md)',
      fontSize: '.875rem',
    }}>
      <span className="status-dot grey" />
      <span style={{ color: 'var(--muted)', flex: 1 }}>Gmail not connected</span>
      <button onClick={handleConnect} disabled={connecting} className="btn btn-primary btn-sm">
        {connecting ? <><Spinner size={13} color="#fff" /> Connecting…</> : 'Connect Gmail'}
      </button>
    </div>
  );
}
