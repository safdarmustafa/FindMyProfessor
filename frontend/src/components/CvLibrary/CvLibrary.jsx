import React, { useState } from 'react';
import Spinner from '../Spinner.jsx';

function formatSize(bytes) {
  if (!bytes) return null;
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

const btn = {
  padding: '.4rem .8rem',
  borderRadius: 'var(--r-sm)',
  fontSize: '.8rem',
  fontWeight: 600,
  cursor: 'pointer',
  border: '1px solid var(--line)',
  background: 'var(--card)',
  color: 'var(--ink)',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '.35rem',
};

/**
 * "Your CVs" — every uploaded CV version with its state, and the actions a
 * student needs: upload a new version, choose which one is active (used for
 * matching and email drafts), and delete old ones. Deleting asks for an
 * inline confirmation rather than a browser dialog.
 */
export default function CvLibrary({ versions, loading, busyId, error, onUploadNew, onMakeActive, onDelete, onRemoveMissing }) {
  const [confirmingId, setConfirmingId] = useState(null);
  const [confirmingCleanup, setConfirmingCleanup] = useState(false);
  const active = versions.find(v => v.is_default);
  const missing = versions.filter(v => v.file_available === false);

  return (
    <section
      aria-label="Your CVs"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-xl)',
        padding: '1.5rem 1.75rem',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '1.5rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--navy)', margin: 0 }}>Your CVs</h2>
          <p style={{ color: 'var(--muted)', fontSize: '.8125rem', margin: '.2rem 0 0' }}>
            The active CV is used for professor matching and attached to your emails.
          </p>
        </div>
        <button type="button" onClick={onUploadNew} style={{ ...btn, background: 'var(--navy)', color: '#fff', border: 'none' }}>
          + Upload new CV
        </button>
      </div>

      {active && active.file_available === false && (
        <div className="banner banner-warning" style={{ marginBottom: '1rem' }}>
          The file for your active CV is no longer stored on the server, so it cannot be attached to emails.
          Please upload your CV again.
        </div>
      )}
      {error && <div className="banner banner-error" style={{ marginBottom: '1rem' }}>{error}</div>}

      {!loading && missing.length > 1 && onRemoveMissing && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '.6rem', flexWrap: 'wrap', marginBottom: '1rem', fontSize: '.8125rem', color: 'var(--ink-2)' }}>
          <span>{missing.length} CVs have missing files and cannot be used.</span>
          {confirmingCleanup ? (
            <span style={{ display: 'inline-flex', gap: '.45rem', alignItems: 'center' }}>
              <span>Delete all {missing.length} permanently?</span>
              <button type="button" style={btn} onClick={() => setConfirmingCleanup(false)} disabled={busyId === 'bulk'}>Cancel</button>
              <button
                type="button"
                style={{ ...btn, background: 'var(--red)', color: '#fff', border: 'none' }}
                disabled={busyId === 'bulk'}
                onClick={async () => { await onRemoveMissing(missing.map(v => v.cv_id)); setConfirmingCleanup(false); }}
              >
                {busyId === 'bulk' ? <><Spinner size={12} color="#fff" /> Removing…</> : 'Remove all'}
              </button>
            </span>
          ) : (
            <button type="button" style={{ ...btn, color: 'var(--red)' }} onClick={() => setConfirmingCleanup(true)}>
              Remove missing CVs
            </button>
          )}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', color: 'var(--muted)', fontSize: '.875rem' }}>
          <Spinner size={14} /> Loading your CVs…
        </div>
      ) : versions.length === 0 ? (
        <p style={{ color: 'var(--muted)', fontSize: '.875rem', margin: 0 }}>You have not uploaded a CV yet.</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '.6rem' }}>
          {versions.map(v => {
            const busy = busyId === v.cv_id;
            const meta = [
              formatDate(v.created_at) && `Uploaded ${formatDate(v.created_at)}`,
              v.file_type && v.file_type.toUpperCase(),
              formatSize(v.file_size),
            ].filter(Boolean).join(' · ');
            return (
              <li
                key={v.cv_id}
                data-testid="cv-row"
                style={{
                  border: `1px solid ${v.is_default ? 'var(--navy)' : 'var(--line)'}`,
                  borderRadius: 'var(--r-md)',
                  padding: '.8rem 1rem',
                  background: v.is_default ? 'var(--bg)' : 'var(--card)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '.75rem', flexWrap: 'wrap' }}>
                  <div style={{ minWidth: 0, flex: '1 1 220px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '.45rem', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '.9rem', wordBreak: 'break-all' }}>{v.file_name}</span>
                      {v.is_default && <span className="badge badge-blue">Active</span>}
                      {v.file_available === false
                        ? <span className="badge badge-red">File missing</span>
                        : v.confirmed
                          ? <span className="badge badge-green">Confirmed</span>
                          : <span className="badge badge-amber">Needs review</span>}
                    </div>
                    {meta && <div style={{ color: 'var(--muted)', fontSize: '.78rem', marginTop: '.2rem' }}>{meta}</div>}
                  </div>

                  {confirmingId === v.cv_id ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '.45rem', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '.8rem', color: 'var(--ink-2)' }}>Delete permanently?</span>
                      <button type="button" style={btn} onClick={() => setConfirmingId(null)} disabled={busy}>Cancel</button>
                      <button
                        type="button"
                        style={{ ...btn, background: 'var(--red)', color: '#fff', border: 'none' }}
                        onClick={async () => { await onDelete(v.cv_id); setConfirmingId(null); }}
                        disabled={busy}
                      >
                        {busy ? <><Spinner size={12} color="#fff" /> Deleting…</> : 'Delete'}
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '.45rem', flexWrap: 'wrap' }}>
                      {!v.is_default && v.file_available !== false && (
                        <button type="button" style={btn} onClick={() => onMakeActive(v.cv_id)} disabled={busy}>
                          {busy ? <><Spinner size={12} /> Switching…</> : 'Make active'}
                        </button>
                      )}
                      <button
                        type="button"
                        style={{ ...btn, color: 'var(--red)' }}
                        onClick={() => setConfirmingId(v.cv_id)}
                        disabled={busy}
                        aria-label={`Delete ${v.file_name}`}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
