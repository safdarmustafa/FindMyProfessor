import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import WhyMatch from '../WhyMatch/WhyMatch.jsx';
import OpportunityCard from '../OpportunityCard/OpportunityCard.jsx';

function nestedName(value) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  return value.name || value.title || '';
}

/* ── tiny helpers ─────────────────────────────────── */
function priorityBadge(priority) {
  if (!priority) return null;
  const p = priority.toLowerCase();
  if (p === 'high') return { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-bdr)', label: 'High' };
  if (p === 'low')  return { bg: 'var(--line-light)', color: 'var(--subtle)', border: 'var(--line)', label: 'Low' };
  return { bg: 'var(--accent-bg)', color: 'var(--accent)', border: 'var(--accent-bdr)', label: 'Normal' };
}

export default function ProfessorCard({ match, showWhy = false }) {
  const [whyOpen, setWhyOpen] = useState(showWhy);

  const prof = match?.professor || {};
  const rm   = match?.research_match || {};
  const score = rm.score ?? rm.research_score ?? 0;
  const priority = rm.priority || '';
  const overlap = match?.research_overlap || [];
  const evidence = rm.evidence || [];
  const opportunities = match?.university_opportunities || [];
  const hasEmail = !!prof.email;

  const name       = [prof.first_name, prof.last_name].filter(Boolean).join(' ') || prof.name || 'Professor';
  const title      = prof.title || prof.position || '';
  const dept       = nestedName(prof.department) || prof.dept || '';
  const university = nestedName(prof.university) || prof.university_name || prof.institution || '';
  const areas      = (prof.research_areas || prof.research_interests || []).slice(0, 4);
  const profId     = prof.id || prof.professor_id;

  const titleDept  = [title, dept].filter(Boolean).join(' · ');

  // First evidence or overlap snippet
  const firstSignal = evidence[0]
    ? (evidence[0].area || evidence[0].description || '')
    : overlap[0]
      ? (typeof overlap[0] === 'string' ? overlap[0] : overlap[0].area || overlap[0].name || '')
      : '';

  const pb = priorityBadge(priority);

  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-lg)',
        padding: '1.25rem',
        transition: 'box-shadow .18s, transform .18s',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        e.currentTarget.style.transform = 'translateY(-1px)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {/* Row 1: Name + match score */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '.75rem', marginBottom: '.25rem' }}>
        <h2 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '1.0625rem',
          fontWeight: 700,
          color: 'var(--navy)',
          margin: 0,
          lineHeight: 1.3,
          flex: 1,
        }}>
          {name}
        </h2>
        {score > 0 && (
          <span style={{
            background: 'var(--navy)',
            color: '#fff',
            fontSize: '.75rem',
            fontWeight: 700,
            padding: '.2rem .6rem',
            borderRadius: 'var(--r-sm)',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}>
            {score}% match
          </span>
        )}
      </div>

      {/* Row 2: title · dept */}
      {titleDept && (
        <p style={{ fontSize: '.8125rem', color: 'var(--ink-2)', margin: '0 0 .15rem' }}>{titleDept}</p>
      )}

      {/* Row 3: university */}
      {university && (
        <p style={{ fontSize: '.8rem', color: 'var(--muted)', margin: '0 0 .6rem' }}>{university}</p>
      )}

      {/* Research area chips */}
      {areas.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.3rem', marginBottom: '.7rem' }}>
          {areas.map((a, i) => (
            <span key={i} style={{
              background: 'var(--chip)',
              color: 'var(--ink-2)',
              fontSize: '.72rem',
              fontWeight: 500,
              borderRadius: '4px',
              padding: '2px 8px',
            }}>
              {typeof a === 'string' ? a : a.area || a.name || String(a)}
            </span>
          ))}
        </div>
      )}

      {/* Priority badge + email badge in a row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', marginBottom: firstSignal ? '.5rem' : '.7rem', flexWrap: 'wrap' }}>
        {pb && (
          <span style={{
            background: pb.bg, color: pb.color,
            border: `1px solid ${pb.border}`,
            borderRadius: 'var(--r-xs)',
            fontSize: '.72rem', fontWeight: 600,
            padding: '.15rem .5rem',
          }}>
            {pb.label} priority
          </span>
        )}
        {hasEmail && (
          <span style={{
            background: 'var(--green-bg)', color: 'var(--green)',
            border: '1px solid var(--green-bdr)',
            borderRadius: 'var(--r-xs)',
            fontSize: '.72rem', fontWeight: 600,
            padding: '.15rem .5rem',
          }}>
            ✓ Email
          </span>
        )}
        {opportunities.length > 0 && (
          <span style={{
            background: 'var(--accent-bg)', color: 'var(--accent)',
            border: '1px solid var(--accent-bdr)',
            borderRadius: 'var(--r-xs)',
            fontSize: '.72rem', fontWeight: 600,
            padding: '.15rem .5rem',
          }}>
            {opportunities.length} opportunity{opportunities.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Why match snippet (1 line) */}
      {firstSignal && (
        <p style={{
          fontSize: '.8rem', color: 'var(--muted)',
          margin: '0 0 .7rem',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          <span style={{ color: 'var(--ink-2)', fontWeight: 500 }}>Match: </span>{firstSignal}
        </p>
      )}

      {/* Footer: action buttons */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '.5rem',
        paddingTop: '.7rem',
        borderTop: '1px solid var(--line-light)',
      }}>
        <button
          onClick={() => setWhyOpen(v => !v)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '.8rem',
            color: 'var(--accent)',
            padding: '.15rem 0',
            fontWeight: 500,
            marginRight: 'auto',
          }}
        >
          {whyOpen ? 'Hide details' : 'Why this match'}
        </button>

        <Link
          to={`/matches/${profId}`}
          style={{
            fontSize: '.8125rem',
            color: 'var(--ink-2)',
            textDecoration: 'none',
            fontWeight: 500,
            padding: '.3rem .75rem',
            border: '1px solid var(--line)',
            borderRadius: 'var(--r-sm)',
            background: 'var(--card)',
            transition: 'background .12s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--line-light)'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--card)'}
        >
          View Profile
        </Link>

        <Link
          to={`/outreach/compose/${profId}`}
          style={{
            fontSize: '.8125rem',
            color: '#fff',
            textDecoration: 'none',
            fontWeight: 600,
            padding: '.3rem .85rem',
            borderRadius: 'var(--r-sm)',
            background: 'var(--navy)',
            transition: 'background .12s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#233260'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--navy)'}
        >
          Prepare Email →
        </Link>
      </div>

      {/* Why match expanded panel */}
      {whyOpen && (
        <div style={{
          marginTop: '.75rem',
          paddingTop: '.75rem',
          borderTop: '1px solid var(--line)',
        }}>
          <WhyMatch match={match} />

          {opportunities.length > 0 && (
            <div style={{ marginTop: '.75rem' }}>
              <div style={{ fontWeight: 600, color: 'var(--muted)', fontSize: '.75rem', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: '.4rem' }}>
                University Opportunities
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.4rem' }}>
                {opportunities.map((opp, i) => (
                  <OpportunityCard key={i} opportunity={opp} isUniversityWide={true} />
                ))}
              </div>
            </div>
          )}

          {overlap.length > 0 && (
            <div style={{ marginTop: '.75rem' }}>
              <div style={{ fontWeight: 600, color: 'var(--muted)', fontSize: '.75rem', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: '.4rem' }}>
                Research Overlap
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.3rem' }}>
                {overlap.map((area, i) => (
                  <span key={i} style={{
                    background: 'var(--accent-bg)',
                    color: 'var(--accent)',
                    border: '1px solid var(--accent-bdr)',
                    borderRadius: 'var(--r-xs)',
                    padding: '.2rem .5rem',
                    fontSize: '.75rem',
                    fontWeight: 500,
                  }}>
                    {typeof area === 'string' ? area : area.area || area.name || String(area)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
