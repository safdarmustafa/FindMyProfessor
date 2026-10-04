import React, { useState, useEffect, useCallback } from 'react';
import AppShell from '../components/AppShell/AppShell.jsx';
import ProfessorCard from '../components/ProfessorCard/ProfessorCard.jsx';
import { SkeletonCard } from '../components/LoadingState.jsx';
import EmptyState from '../components/EmptyState.jsx';
import ErrorState from '../components/ErrorState.jsx';
import { fetchMatches, fetchUniversities } from '../services/matching.js';
import { fetchProfile } from '../services/profile.js';
import { getProfileId } from '../services/api.js';

// Delay before the single automatic retry on a failed matches load — long
// enough for a cold-starting Render instance to finish waking up.
const MATCHES_RETRY_DELAY_MS = 1500;

const MODE_OPTIONS = [
  { value: 'research', label: 'Research Match' },
  { value: 'opportunity', label: 'Opportunity First' },
  { value: 'both', label: 'Both' },
];

/* ── Metrics strip ────────────────────────────────────── */
function MetricsStrip({ matches }) {
  const total = matches.length;
  const strong = matches.filter(m => {
    const rm = m.research_match || {};
    return (rm.score ?? 0) >= 80 || rm.priority === 'high';
  }).length;
  const outreachReady = matches.filter(m => m.professor?.email).length;
  const withOpps = matches.filter(m => (m.university_opportunities || []).length > 0).length;

  const cells = [
    { label: 'Professors', value: total },
    { label: 'Strong matches', value: strong },
    { label: 'Outreach ready', value: outreachReady },
    { label: 'With opportunities', value: withOpps },
  ];

  return (
    <div style={{
      display: 'flex',
      gap: '0',
      marginBottom: '1.5rem',
      background: 'var(--card)',
      border: '1px solid var(--line)',
      borderRadius: 'var(--r-lg)',
      overflow: 'hidden',
      boxShadow: 'var(--shadow-sm)',
    }}>
      {cells.map((c, i) => (
        <div key={i} style={{
          flex: 1,
          padding: '.9rem 1rem',
          textAlign: 'center',
          borderRight: i < cells.length - 1 ? '1px solid var(--line)' : 'none',
        }}>
          <div style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '1.5rem',
            fontWeight: 700,
            color: 'var(--navy)',
            lineHeight: 1,
            marginBottom: '.2rem',
          }}>{c.value}</div>
          <div style={{ fontSize: '.72rem', color: 'var(--muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '.03em' }}>{c.label}</div>
        </div>
      ))}
    </div>
  );
}

export default function Matches() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [profileConfirmed, setProfileConfirmed] = useState(null);

  // Filters
  const [mode, setMode] = useState('research');
  const [universities, setUniversities] = useState([]);
  const [filters, setFilters] = useState({
    university_id: '',
    min_score: '',
    email_only: false,
    opportunity_type: '',
    opportunity_status: '',
  });
  const [query, setQuery] = useState('');

  const profileId = getProfileId();

  const loadMatches = useCallback(async () => {
    if (!profileId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMatches({ mode, limit: 25, ...filters });
      setMatches(data.matches || []);
    } catch (e) {
      // Production is a real cross-origin request to a Render backend that
      // can cold-start after a period of inactivity — the very first
      // request can fail even though the service is healthy and every
      // later request would succeed. One bounded, delayed retry absorbs
      // that automatically instead of requiring the user to notice the
      // failure and click "Try again" themselves.
      await new Promise(resolve => setTimeout(resolve, MATCHES_RETRY_DELAY_MS));
      try {
        const data = await fetchMatches({ mode, limit: 25, ...filters });
        setMatches(data.matches || []);
      } catch (e2) {
        setError(e2.message);
      }
    } finally {
      setLoading(false);
    }
  }, [profileId, mode, filters]);

  useEffect(() => {
    if (!profileId) {
      setLoading(false);
      return;
    }
    // A failed /profile request (network, CORS, timeout, cold start, etc.)
    // does NOT mean the profile is incomplete — only an actual `confirmed:
    // false` response does. Leaving profileConfirmed untouched on failure
    // avoids a false "Complete your profile" loop; loadMatches() below runs
    // independently and already surfaces its own retryable error state if
    // the backend is genuinely unreachable.
    fetchProfile()
      .then(p => setProfileConfirmed(p.confirmed))
      .catch(() => {});

    fetchUniversities()
      .then(d => setUniversities(d.universities || []))
      .catch(() => {});

    loadMatches();
  }, [profileId]); // eslint-disable-line react-hooks/exhaustive-deps

  const [didInit, setDidInit] = useState(false);
  useEffect(() => {
    if (!didInit) { setDidInit(true); return; }
    loadMatches();
  }, [mode, filters]); // eslint-disable-line react-hooks/exhaustive-deps

  const ff = (k) => (e) => setFilters(f => ({
    ...f,
    [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value,
  }));

  const visibleMatches = matches.filter(m => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    const p = m.professor || {};
    const name = [p.first_name, p.last_name, p.name].filter(Boolean).join(' ').toLowerCase();
    const uni = (p.university?.name || p.university_name || '').toLowerCase();
    return name.includes(q) || uni.includes(q);
  });

  if (!profileId) {
    return (
      <AppShell>
        <EmptyState
          title="No profile yet"
          description="Upload your CV to get started with professor matching."
          actionLabel="Upload CV"
          actionHref="/onboarding"
        />
      </AppShell>
    );
  }

  if (profileConfirmed === false) {
    return (
      <AppShell>
        <EmptyState
          title="Confirm your CV profile"
          description="Please complete your profile setup before viewing research matches."
          actionLabel="Complete profile setup"
          actionHref="/onboarding"
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div style={{ minHeight: 'calc(100vh - var(--nav-h))', background: 'var(--bg)', padding: '2rem 1.5rem' }}>
        <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>

          {/* ── Page header ───────────────────────────── */}
          <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h1 style={{
                fontFamily: 'var(--font-serif)',
                fontSize: 'clamp(1.3rem, 3vw, 1.6rem)',
                color: 'var(--navy)',
                marginBottom: '.3rem',
              }}>
                Research Matches
              </h1>
              <p style={{ fontSize: '.875rem', color: 'var(--muted)' }}>
                Faculty whose work aligns with your research background.
              </p>
            </div>

            {/* Mode toggle */}
            <div style={{
              display: 'flex',
              gap: '.25rem',
              background: 'var(--card)',
              border: '1px solid var(--line)',
              borderRadius: 'var(--r-md)',
              padding: '.2rem',
              boxShadow: 'var(--shadow-sm)',
            }}>
              {MODE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setMode(opt.value)}
                  style={{
                    padding: '.35rem .85rem',
                    borderRadius: 'var(--r-sm)',
                    fontSize: '.8125rem',
                    fontWeight: mode === opt.value ? 600 : 500,
                    background: mode === opt.value ? 'var(--navy)' : 'transparent',
                    color: mode === opt.value ? '#fff' : 'var(--muted)',
                    border: 'none',
                    cursor: 'pointer',
                    transition: 'all .12s',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* ── Filter bar ────────────────────────────── */}
          <div style={{
            display: 'flex',
            gap: '.65rem',
            flexWrap: 'wrap',
            marginBottom: '1.5rem',
            padding: '1rem 1.25rem',
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: 'var(--r-lg)',
            boxShadow: 'var(--shadow-sm)',
            alignItems: 'center',
          }}>
            <input
              type="search"
              className="form-input"
              placeholder="Search professors"
              value={query}
              onChange={e => setQuery(e.target.value)}
              style={{ flex: '1 0 180px', maxWidth: '240px' }}
            />

            <select
              className="form-select"
              value={filters.university_id}
              onChange={ff('university_id')}
              style={{ flex: '1 0 160px', maxWidth: '220px' }}
            >
              <option value="">All universities</option>
              {universities.map(u => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>

            <input
              type="number"
              className="form-input"
              placeholder="Min score"
              value={filters.min_score}
              onChange={ff('min_score')}
              min={0} max={100}
              style={{ flex: '0 0 110px' }}
            />

            <select
              className="form-select"
              value={filters.opportunity_type}
              onChange={ff('opportunity_type')}
              style={{ flex: '1 0 140px', maxWidth: '180px' }}
            >
              <option value="">All opp. types</option>
              <option value="phd">PhD</option>
              <option value="masters">Masters</option>
              <option value="postdoc">Postdoc</option>
              <option value="research_assistant">Research Assistant</option>
            </select>

            <select
              className="form-select"
              value={filters.opportunity_status}
              onChange={ff('opportunity_status')}
              style={{ flex: '1 0 130px', maxWidth: '160px' }}
            >
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="rolling">Rolling</option>
              <option value="closed">Closed</option>
            </select>

            <button
              onClick={loadMatches}
              style={{
                marginLeft: 'auto',
                padding: '.4rem .9rem',
                background: 'var(--navy)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--r-sm)',
                fontSize: '.8125rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Apply filters
            </button>
          </div>

          {/* ── Metrics strip ─────────────────────────── */}
          {!loading && visibleMatches.length > 0 && <MetricsStrip matches={visibleMatches} />}

          {/* ── Results ───────────────────────────────── */}
          {loading && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
              <SkeletonCard /><SkeletonCard /><SkeletonCard />
            </div>
          )}

          {!loading && error && (
            <ErrorState title="Failed to load matches" message={error} onRetry={loadMatches} />
          )}

          {!loading && !error && visibleMatches.length === 0 && (
            <EmptyState
              title="No matches found"
              description="Try adjusting your filters or mode to find more professors."
              action={loadMatches}
              actionLabel="Reset and reload"
            />
          )}

          {!loading && !error && visibleMatches.length > 0 && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              gap: '1rem',
            }}>
              {visibleMatches.map((match, i) => (
                <ProfessorCard key={match.professor?.id || i} match={match} />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
