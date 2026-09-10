import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import AppShell from '../components/AppShell/AppShell.jsx';
import StatusBadge from '../components/StatusBadge/StatusBadge.jsx';
import LoadingState from '../components/LoadingState.jsx';
import EmptyState from '../components/EmptyState.jsx';
import ErrorState from '../components/ErrorState.jsx';
import { listHistory } from '../services/outreach.js';
import { getProfileId } from '../services/api.js';

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return iso; }
}

function nestedName(value) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  return value.name || value.title || '';
}

function professorLabel(item) {
  return nestedName(item.professor_name)
    || nestedName(item.professor)
    || [item.first_name, item.last_name].filter(Boolean).join(' ')
    || '';
}

function universityLabel(item) {
  return nestedName(item.university_name)
    || nestedName(item.university)
    || nestedName(item.professor?.university)
    || '';
}

/* Status badge pill */
function StatusPill({ status }) {
  const s = (status || 'draft').toLowerCase();
  const map = {
    draft:  { bg: 'var(--line-light)', color: 'var(--muted)',  border: 'var(--line)', label: 'Draft' },
    generated: { bg: 'var(--line-light)', color: 'var(--muted)',  border: 'var(--line)', label: 'Draft' },
    edited: { bg: 'var(--line-light)', color: 'var(--muted)',  border: 'var(--line)', label: 'Draft' },
    ready:  { bg: 'var(--accent-bg)',  color: 'var(--accent)', border: 'var(--accent-bdr)', label: 'Ready' },
    sent:   { bg: 'var(--green-bg)',   color: 'var(--green)',  border: 'var(--green-bdr)', label: 'Sent' },
    failed: { bg: 'var(--red-bg)',     color: 'var(--red)',    border: '#fecaca', label: 'Failed' },
  };
  const style = map[s] || map.draft;
  return (
    <span style={{
      display: 'inline-block',
      padding: '.15rem .55rem',
      background: style.bg,
      color: style.color,
      border: `1px solid ${style.border}`,
      borderRadius: 'var(--r-xs)',
      fontSize: '.72rem',
      fontWeight: 600,
      letterSpacing: '.02em',
    }}>
      {style.label}
    </span>
  );
}

export default function OutreachHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const profileId = getProfileId();

  const loadHistory = async () => {
    if (!profileId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listHistory();
      setHistory(data || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadHistory(); }, [profileId]);

  if (!profileId) {
    return (
      <AppShell>
        <EmptyState
          title="No profile yet"
          description="Set up your profile to start your outreach journey."
          actionLabel="Get started"
          actionHref="/onboarding"
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div style={{ minHeight: 'calc(100vh - var(--nav-h))', background: 'var(--bg)', padding: '2rem 1.5rem' }}>
        <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>

          {/* ── Header ───────────────────────────────── */}
          <div style={{ marginBottom: '1.75rem' }}>
            <h1 style={{
              fontFamily: 'var(--font-serif)',
              fontSize: 'clamp(1.3rem, 3vw, 1.6rem)',
              color: 'var(--navy)',
              marginBottom: '.3rem',
            }}>
              Outreach History
            </h1>
            <p style={{ fontSize: '.875rem', color: 'var(--muted)' }}>
              All your email drafts and sent outreach.
            </p>
          </div>

          {loading && <LoadingState message="Loading outreach history…" />}
          {!loading && error && <ErrorState title="Failed to load history" message={error} onRetry={loadHistory} />}

          {!loading && !error && history.length === 0 && (
            <EmptyState
              title="No outreach history yet."
              description={<>Discover professors and start drafting personalized emails. <Link to="/matches" style={{ color: 'var(--accent)' }}>Start by finding a professor match.</Link></>}
              actionLabel="Browse Research Matches"
              actionHref="/matches"
            />
          )}

          {!loading && !error && history.length > 0 && (
            <>
              {/* ── Desktop table ─────────────────────── */}
              <div
                data-desktop
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-lg)',
                  overflow: 'hidden',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.875rem' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg)', borderBottom: '1px solid var(--line)' }}>
                      {['Professor', 'University', 'Subject', 'Status', 'Sent', 'Actions'].map((h, i) => (
                        <th key={i} style={{
                          padding: '.75rem 1rem',
                          textAlign: 'left',
                          fontWeight: 600,
                          color: 'var(--muted)',
                          fontSize: '.72rem',
                          letterSpacing: '.04em',
                          textTransform: 'uppercase',
                          whiteSpace: 'nowrap',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item, i) => (
                      <tr key={item.draft_id || i}
                        style={{ borderBottom: i < history.length - 1 ? '1px solid var(--line-light)' : 'none' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '.8rem 1rem', fontWeight: 600, color: 'var(--navy)' }}>
                          {professorLabel(item) || '—'}
                        </td>
                        <td style={{ padding: '.8rem 1rem', color: 'var(--muted)', fontSize: '.8125rem' }}>
                          {universityLabel(item) || '—'}
                        </td>
                        <td style={{ padding: '.8rem 1rem', color: 'var(--ink-2)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.subject || '—'}
                        </td>
                        <td style={{ padding: '.8rem 1rem' }}>
                          <StatusPill status={item.status || 'draft'} />
                        </td>
                        <td style={{ padding: '.8rem 1rem', color: 'var(--muted)', whiteSpace: 'nowrap', fontSize: '.8125rem' }}>
                          {formatDate(item.sent_at)}
                        </td>
                        <td style={{ padding: '.8rem 1rem' }}>
                          {item.professor_id && (
                            <Link
                              to={`/outreach/compose/${item.professor_id}`}
                              style={{
                                display: 'inline-flex', alignItems: 'center',
                                padding: '.3rem .75rem',
                                background: 'var(--card)', color: 'var(--ink)',
                                border: '1px solid var(--line)', borderRadius: 'var(--r-sm)',
                                textDecoration: 'none', fontSize: '.8rem', fontWeight: 500,
                              }}
                            >
                              Compose again
                            </Link>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* ── Mobile stacked cards ──────────────── */}
              <div className="history-mobile-cards" style={{ display: 'none' }}>
                {history.map((item, i) => (
                  <div key={item.draft_id || i} style={{
                    background: 'var(--card)',
                    border: '1px solid var(--line)',
                    borderRadius: 'var(--r-lg)',
                    padding: '1rem',
                    marginBottom: '.65rem',
                    boxShadow: 'var(--shadow-sm)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '.4rem' }}>
                      <div style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '.9rem' }}>{professorLabel(item) || '—'}</div>
                      <StatusPill status={item.status || 'draft'} />
                    </div>
                    <div style={{ fontSize: '.8rem', color: 'var(--muted)', marginBottom: '.3rem' }}>{universityLabel(item) || '—'}</div>
                    {item.subject && <div style={{ fontSize: '.8125rem', color: 'var(--ink-2)', marginBottom: '.6rem' }}>{item.subject}</div>}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '.75rem', color: 'var(--subtle)' }}>{formatDate(item.sent_at)}</span>
                      {item.professor_id && (
                        <Link to={`/outreach/compose/${item.professor_id}`} style={{
                          display: 'inline-flex', alignItems: 'center',
                          padding: '.3rem .7rem',
                          background: 'var(--card)', color: 'var(--ink)',
                          border: '1px solid var(--line)', borderRadius: 'var(--r-sm)',
                          textDecoration: 'none', fontSize: '.8rem', fontWeight: 500,
                        }}>
                          Compose again
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <style>{`
        @media (max-width: 640px) {
          [data-desktop] { display: none !important; }
          .history-mobile-cards { display: block !important; }
        }
      `}</style>
    </AppShell>
  );
}
