import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import AppShell from '../components/AppShell/AppShell.jsx';
import MatchScore from '../components/MatchScore/MatchScore.jsx';
import WhyMatch from '../components/WhyMatch/WhyMatch.jsx';
import ResearchAreas from '../components/ResearchAreas/ResearchAreas.jsx';
import OpportunityCard from '../components/OpportunityCard/OpportunityCard.jsx';
import LoadingState from '../components/LoadingState.jsx';
import ErrorState from '../components/ErrorState.jsx';
import { getAlignmentLabel, getAlignmentText, getAlignmentClass } from '../components/StatusBadge/StatusBadge.jsx';
import { fetchMatches, fetchProfessor } from '../services/matching.js';
import { getProfileId } from '../services/api.js';

function nestedName(value) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  return value.name || value.title || '';
}

/* ── Section card helper ─────────────────────────────── */
function Section({ title, children }) {
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
        padding: '.8rem 1.5rem',
        borderBottom: '1px solid var(--line-light)',
        background: 'var(--bg)',
      }}>
        <h3 style={{ fontSize: '.8125rem', fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', margin: 0 }}>
          {title}
        </h3>
      </div>
      <div style={{ padding: '1.25rem 1.5rem' }}>
        {children}
      </div>
    </div>
  );
}

export default function ProfessorDetail() {
  const { id } = useParams();
  const [prof, setProf] = useState(null);
  const [match, setMatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);

    // fetchProfessor is the fast, required lookup for this page's core
    // content. fetchMatches({limit:100}) is only used to find this one
    // professor's match evidence (Why You Match, opportunities) — it
    // re-scores every professor and is measurably slow. Blocking the whole
    // page on it made this page (and the "Prepare Email" click that
    // follows it) feel broken/unresponsive. The match-dependent sections
    // below already render conditionally on `match`, so they simply
    // appear a moment later instead of holding up the whole page.
    fetchProfessor(id)
      .then(profData => { if (profData) setProf(profData); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));

    fetchMatches({ limit: 100 })
      .then(d => (d.matches || []).find(m => {
        const p = m.professor || {};
        return String(p.id) === String(id) || String(p.professor_id) === String(id);
      }))
      .then(matchData => {
        if (matchData) {
          setMatch(matchData);
          setProf(prev => prev || matchData.professor || null);
        }
      })
      .catch(() => {});
  }, [id]);

  if (loading) return <AppShell><LoadingState message="Loading professor profile…" fullPage /></AppShell>;
  if (error)   return <AppShell><ErrorState title="Failed to load professor" message={error} /></AppShell>;
  if (!prof)   return <AppShell><ErrorState title="Professor not found" /></AppShell>;

  const name       = [prof.first_name, prof.last_name].filter(Boolean).join(' ') || prof.name || 'Professor';
  const title      = prof.title || prof.position || '';
  const dept       = nestedName(prof.department) || prof.dept || '';
  const university = nestedName(prof.university) || prof.university_name || prof.institution || '';
  const lab        = nestedName(prof.lab) || prof.laboratory || '';
  const website    = prof.website || prof.faculty_url || prof.url || '';
  const areas      = prof.research_areas || prof.research_interests || [];
  const email      = prof.email || '';

  const rm   = match?.research_match || {};
  const score    = rm.score ?? rm.research_score ?? 0;
  const priority = rm.priority || '';
  const overlap  = match?.research_overlap || [];
  const opportunities = match?.university_opportunities || [];

  const level     = getAlignmentLabel(score, priority);
  const alignText = getAlignmentText(level);
  const alignClass= getAlignmentClass(level);

  return (
    <AppShell>
      <div style={{ minHeight: 'calc(100vh - var(--nav-h))', background: 'var(--bg)', padding: '2rem 1.5rem 5rem' }}>
        <div style={{ maxWidth: '820px', margin: '0 auto' }}>

          {/* Back link */}
          <Link to="/matches" style={{
            display: 'inline-flex', alignItems: 'center', gap: '.35rem',
            fontSize: '.875rem', color: 'var(--muted)', marginBottom: '1.5rem',
            textDecoration: 'none', fontWeight: 500,
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--navy)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 5l-7 7 7 7"/>
            </svg>
            Research Matches
          </Link>

          {/* ── Hero card — left navy accent ─────────── */}
          <div style={{
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: 'var(--r-lg)',
            borderLeft: '4px solid var(--navy)',
            padding: '1.75rem 2rem',
            marginBottom: '1rem',
            boxShadow: 'var(--shadow-sm)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1.5rem', flexWrap: 'wrap' }}>
              <div style={{ flex: 1 }}>
                <h1 style={{
                  fontFamily: 'var(--font-serif)',
                  fontSize: 'clamp(1.3rem, 3vw, 1.75rem)',
                  fontWeight: 700,
                  color: 'var(--navy)',
                  marginBottom: '.4rem',
                }}>
                  {name}
                </h1>
                {title      && <p style={{ fontSize: '.9rem', color: 'var(--ink-2)', marginBottom: '.2rem' }}>{title}</p>}
                {dept       && <p style={{ fontSize: '.875rem', color: 'var(--ink-2)', marginBottom: '.2rem' }}>{dept}</p>}
                {university && <p style={{ fontSize: '.875rem', color: 'var(--muted)', marginBottom: '.35rem' }}>{university}</p>}
                {lab        && <p style={{ fontSize: '.8125rem', color: 'var(--muted)', marginBottom: '.25rem' }}>Lab: {lab}</p>}
                {website    && (
                  <a href={website} target="_blank" rel="noopener noreferrer" style={{ fontSize: '.8125rem', color: 'var(--accent)' }}>
                    Faculty website →
                  </a>
                )}
              </div>

              {match && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '.5rem' }}>
                  <MatchScore score={score} priority={priority} />
                  {email ? (
                    <span className="badge badge-green">✓ Outreach ready</span>
                  ) : (
                    <span className="badge badge-grey">Discovery</span>
                  )}
                </div>
              )}
            </div>

            {areas.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <ResearchAreas areas={areas} />
              </div>
            )}
          </div>

          {/* ── Research Focus / Why Match ────────────── */}
          {match && (
            <Section title="Why You Match">
              <WhyMatch match={match} />
            </Section>
          )}

          {/* ── Research Overlap ─────────────────────── */}
          {overlap.length > 0 && (
            <Section title="Research Areas in Common">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem' }}>
                {overlap.map((area, i) => (
                  <span key={i} style={{
                    background: 'var(--accent-bg)',
                    color: 'var(--accent)',
                    border: '1px solid var(--accent-bdr)',
                    borderRadius: 'var(--r-xs)',
                    padding: '.25rem .65rem',
                    fontSize: '.8rem',
                    fontWeight: 500,
                  }}>
                    {typeof area === 'string' ? area : area.area || area.name || String(area)}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* ── Research Opportunity ─────────────────── */}
          {opportunities.length > 0 && (
            <Section title="Research Opportunities">
              <p style={{ fontSize: '.8125rem', color: 'var(--muted)', marginBottom: '.75rem' }}>
                These are university-wide positions, not specific to this professor.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
                {opportunities.map((opp, i) => (
                  <OpportunityCard key={i} opportunity={opp} isUniversityWide={true} />
                ))}
              </div>
            </Section>
          )}

          {/* ── Contact ──────────────────────────────── */}
          {email && (
            <Section title="Contact">
              <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', fontSize: '.875rem' }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                  <polyline points="22,6 12,13 2,6"/>
                </svg>
                <span style={{ color: 'var(--ink-2)', fontWeight: 500 }}>{email}</span>
                <span className="badge badge-green" style={{ fontSize: '.7rem' }}>Available</span>
              </div>
            </Section>
          )}

        </div>
      </div>

      {/* ── Sticky bottom CTA ────────────────────────── */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: '#fff',
        borderTop: '1px solid var(--line)',
        padding: '.9rem 1.5rem',
        zIndex: 50,
        display: 'flex',
        justifyContent: 'center',
        gap: '.75rem',
        boxShadow: '0 -2px 12px rgba(0,0,0,.06)',
      }}>
        <Link to="/matches" style={{
          padding: '.65rem 1.25rem',
          background: 'var(--card)',
          color: 'var(--ink)',
          border: '1px solid var(--line)',
          borderRadius: 'var(--r-md)',
          textDecoration: 'none',
          fontSize: '.875rem',
          fontWeight: 500,
        }}>
          ← Back to Matches
        </Link>
        <Link
          to={`/outreach/compose/${id}`}
          style={{
            padding: '.65rem 1.5rem',
            background: 'var(--navy)',
            color: '#fff',
            borderRadius: 'var(--r-md)',
            textDecoration: 'none',
            fontSize: '.9375rem',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '.4rem',
          }}
        >
          Prepare Personalized Email →
        </Link>
      </div>
    </AppShell>
  );
}
