import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import NetworkMotif from '../components/NetworkMotif.jsx';

const DISPLAY = "'Fraunces', Georgia, 'Times New Roman', Times, serif";

const FOUNDING_TEAM = [
  {
    name: 'Safdar Mustafa',
    designation: 'Undergraduate Student, Jamia Hamdard',
    role: 'Founder & Product Lead',
    photo: '/team/safdar-mustafa.jpg',
    alt: 'Portrait of Safdar Mustafa, Founder & Product Lead of FindMyProfessor',
    paragraphs: [
      'Safdar is an undergraduate student at Jamia Hamdard building FindMyProfessor around a problem students repeatedly run into: finding the right professors, research groups, labs, and opportunities is often harder than it should be.',
      'The product is shaped around a simple idea: make academic discovery more structured, more personalized, and easier to act on. FindMyProfessor brings together university information, professor research areas, opportunity discovery, research matching, and personalized outreach into one student-focused workflow.',
    ],
    closing: 'Building FindMyProfessor is about making the first step toward research feel a little less difficult for every student.',
  },
  {
    name: 'Dayam Nadeem',
    designation: 'Software Engineer II, InEvo AI',
    role: 'Co-Founder',
    photo: '/team/dayam-nadeem.jpg',
    alt: 'Portrait of Dayam Nadeem, Co-Founder of FindMyProfessor',
    paragraphs: [
      'Dayam brings professional software engineering experience to the founding team, contributing to the development and evolution of FindMyProfessor alongside his work at InEvo AI.',
      'As Co-Founder, he works with the founding team on the product’s technical direction, helping shape how the platform is built and how it continues to grow.',
    ],
    closing: 'The focus stays on building technology that’s genuinely useful for the students who rely on it.',
  },
];

const TECHNICAL_CONTRIBUTION = {
  name: 'Md Rehaan Alam',
  designation: 'Undergraduate Student, Galgotias University',
  role: 'Lead Android Developer',
  photo: '/team/rehaan-alam.jpg',
  alt: 'Portrait of Md Rehaan Alam, Lead Android Developer of FindMyProfessor',
  paragraphs: [
    'Rehaan contributes to FindMyProfessor as its Lead Android Developer, part of the technical team helping bring the product’s experience to mobile users.',
    'His work is focused on turning the product’s vision into a practical, usable mobile experience: the kind students can rely on when they’re actually searching for a professor or an opportunity.',
  ],
  closing: 'It’s about building technology that students can actually use.',
};

const MENTOR = {
  name: 'Dr. Shahab Saquib Sohail',
  designation: 'Assistant Professor, Jamia Hamdard',
  role: 'Faculty Mentor & Academic Advisor',
  photo: '/team/shahab-saquib-sohail.jpg',
  alt: 'Portrait of Dr. Shahab Saquib Sohail, Faculty Mentor & Academic Advisor of FindMyProfessor',
  paragraphs: [
    'Dr. Shahab Saquib Sohail is an Assistant Professor of Computer Science & Engineering at Jamia Hamdard, New Delhi, with a Ph.D. in Computer Science from Aligarh Muslim University.',
    'His research focuses on AI, computational intelligence, recommender systems, and computational social science. He has 125+ SCI indexed publications and 4,000+ Google Scholar citations, with recognition among the top 2% of AI and computer vision researchers by Stanford and Elsevier.',
    'He actively mentors students and collaborates internationally in artificial intelligence and machine learning.',
  ],
  closing: 'Academic guidance like this helps keep the platform grounded in how research and mentorship actually work.',
};

/* ── Shared section eyebrow + heading block ──────────────── */
function SectionIntro({ eyebrow, title, desc }) {
  return (
    <div style={{ marginBottom: '3rem', maxWidth: '640px' }}>
      <div style={{ fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--brass-ink)', marginBottom: '.6rem' }}>
        {eyebrow}
      </div>
      <h2 style={{
        fontFamily: DISPLAY,
        fontSize: 'clamp(1.5rem, 3vw, 2rem)',
        fontWeight: 600,
        color: 'var(--navy)',
        marginBottom: desc ? '.6rem' : 0,
        letterSpacing: '-.01em',
        textWrap: 'balance',
      }}>
        {title}
      </h2>
      {desc && (
        <p style={{ color: 'var(--muted)', fontSize: '.9375rem', lineHeight: 1.65 }}>{desc}</p>
      )}
    </div>
  );
}

/* ── Large editorial profile: portrait on one side, name / designation /
     role / narrative / closing statement on the other. This replaces the
     old small circular-avatar card — the photograph is now a primary
     visual element, not a decoration. ── */
function ProfileRow({ person, reverse }) {
  return (
    <div className={`profile-row${reverse ? ' profile-row--reverse' : ''}`}>
      <div className="profile-row-photo">
        <img
          src={person.photo}
          alt={person.alt}
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top', display: 'block' }}
        />
      </div>
      <div className="profile-row-text">
        <h3 style={{ fontFamily: DISPLAY, fontSize: 'clamp(1.35rem, 2.4vw, 1.7rem)', fontWeight: 600, color: 'var(--navy)', marginBottom: '.3rem', letterSpacing: '-.01em' }}>
          {person.name}
        </h3>
        <p style={{ fontSize: '.9375rem', color: 'var(--muted)', marginBottom: '.85rem' }}>
          {person.designation}
        </p>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '.35rem .85rem',
          borderRadius: 'var(--r-xs)',
          fontSize: '.78rem',
          fontWeight: 700,
          letterSpacing: '.01em',
          background: 'var(--brass-bg)',
          color: 'var(--brass-ink)',
          border: '1px solid rgba(201,164,99,.35)',
          marginBottom: '1.4rem',
        }}>
          {person.role}
        </span>
        {person.paragraphs.map((p, i) => (
          <p key={i} style={{ fontSize: '.9375rem', color: 'var(--ink-2)', lineHeight: 1.75, marginBottom: '1rem' }}>
            {p}
          </p>
        ))}
        <p style={{
          fontFamily: DISPLAY,
          fontStyle: 'italic',
          fontSize: '1.02rem',
          color: 'var(--navy)',
          lineHeight: 1.6,
          borderLeft: '2px solid var(--brass)',
          paddingLeft: '1rem',
          marginTop: '1.4rem',
        }}>
          {person.closing}
        </p>
      </div>
    </div>
  );
}

export default function Team() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div style={{ minHeight: '100vh', background: '#fff' }}>

      {/* ── Standalone header (matches Home.jsx) ─────────── */}
      <header style={{
        background: 'rgba(255,255,255,.92)',
        backdropFilter: 'blur(8px)',
        borderBottom: '1px solid var(--line)',
        height: 'var(--nav-h)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{
          maxWidth: 'var(--content-max)',
          margin: '0 auto',
          padding: '0 1.5rem',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
        }}>
          <Link to="/" style={{
            fontFamily: DISPLAY,
            fontSize: '1.15rem',
            fontWeight: 600,
            color: 'var(--navy)',
            flex: 1,
            letterSpacing: '-.01em',
            textDecoration: 'none',
          }}>
            FindMyProfessor
          </Link>
          <nav className="public-nav-links">
            <Link to="/login" className="public-nav-link">Login</Link>
            <Link to="/login" className="public-nav-link">Get Started</Link>
            <Link to="/team" className="public-nav-link">About Us</Link>
          </nav>
          <button
            type="button"
            className="public-nav-hamburger"
            onClick={() => setMenuOpen(v => !v)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {menuOpen
                ? <path d="M18 6L6 18M6 6l12 12"/>
                : <path d="M3 12h18M3 6h18M3 18h18"/>
              }
            </svg>
          </button>
        </div>
        {menuOpen && (
          <div className="public-nav-mobile-menu">
            <Link to="/login" className="public-nav-mobile-link" onClick={() => setMenuOpen(false)}>Login</Link>
            <Link to="/login" className="public-nav-mobile-link" onClick={() => setMenuOpen(false)}>Get Started</Link>
            <Link to="/team" className="public-nav-mobile-link" onClick={() => setMenuOpen(false)}>About Us</Link>
          </div>
        )}
      </header>

      {/* ── Hero ─────────────────────────────────────── */}
      <section style={{
        position: 'relative',
        overflow: 'hidden',
        background: 'linear-gradient(160deg, var(--navy-mid) 0%, var(--navy-deep) 100%)',
        padding: '4.5rem 1.5rem 5rem',
        textAlign: 'center',
      }}>
        <NetworkMotif opacity={0.4} />
        <div style={{ position: 'relative', maxWidth: '680px', margin: '0 auto' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '.4rem',
            background: 'rgba(201,164,99,.12)',
            border: '1px solid rgba(201,164,99,.4)',
            borderRadius: '999px',
            padding: '.32rem .85rem .32rem .65rem',
            fontSize: '.72rem',
            color: 'var(--brass-soft)',
            fontWeight: 600,
            letterSpacing: '.06em',
            textTransform: 'uppercase',
            marginBottom: '1.5rem',
          }}>
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--brass)' }} />
            The Team
          </div>

          <h1 style={{
            fontFamily: DISPLAY,
            fontSize: 'clamp(2rem, 4.2vw, 3rem)',
            fontWeight: 600,
            color: '#fff',
            lineHeight: 1.18,
            letterSpacing: '-.01em',
            marginBottom: '1.25rem',
            textWrap: 'balance',
          }}>
            The People Behind <em style={{ fontStyle: 'italic', color: 'var(--brass-soft)', fontWeight: 500 }}>FindMyProfessor</em>
          </h1>

          <p style={{
            fontSize: '1.02rem',
            color: 'rgba(255,255,255,.62)',
            lineHeight: 1.75,
            maxWidth: '560px',
            margin: '0 auto',
          }}>
            FindMyProfessor is being built through a combination of student-driven product
            development, technical expertise, and academic mentorship.
          </p>
        </div>
      </section>

      {/* ── Founding Team ────────────────────────────── */}
      <section style={{ padding: '5.5rem 1.5rem', background: '#fff' }}>
        <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>
          <SectionIntro eyebrow="Origin" title="Founding Team" />
          {FOUNDING_TEAM.map((person, i) => (
            <ProfileRow key={person.name} person={person} reverse={i % 2 === 1} />
          ))}
        </div>
      </section>

      {/* ── Technical Contribution ───────────────────── */}
      <section style={{ padding: '5.5rem 1.5rem', background: 'var(--bg)' }}>
        <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>
          <SectionIntro eyebrow="Engineering" title="Technical Contribution" />
          <ProfileRow person={TECHNICAL_CONTRIBUTION} />
        </div>
      </section>

      {/* ── Academic Mentorship — deliberately distinct, editorial treatment ── */}
      <section style={{ padding: '5.5rem 1.5rem 6rem', background: '#fff' }}>
        <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>
          <SectionIntro
            eyebrow="Guidance"
            title="Academic Mentorship"
            desc="A pillar of FindMyProfessor in its own right, bringing academic perspective, credibility, and guidance that shape the project's vision."
          />

          <div className="mentor-panel" style={{
            background: 'linear-gradient(160deg, var(--navy-mid) 0%, var(--navy-deep) 100%)',
            borderRadius: 'var(--r-xl)',
            position: 'relative',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <NetworkMotif opacity={0.25} />
            <div className="mentor-panel-inner">
              <div className="mentor-photo">
                <img
                  src={MENTOR.photo}
                  alt={MENTOR.alt}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top', display: 'block' }}
                />
              </div>
              <div className="mentor-text">
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '.4rem',
                  fontSize: '.72rem',
                  fontWeight: 700,
                  letterSpacing: '.08em',
                  textTransform: 'uppercase',
                  color: 'var(--brass-soft)',
                  marginBottom: '.9rem',
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--brass)" strokeWidth="2">
                    <path d="M22 10 12 5 2 10l10 5 10-5Z" />
                    <path d="M6 12v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5" />
                  </svg>
                  Faculty Mentor &amp; Academic Advisor
                </div>
                <h3 style={{
                  fontFamily: DISPLAY,
                  fontSize: 'clamp(1.5rem, 3vw, 2rem)',
                  fontWeight: 600,
                  color: '#fff',
                  marginBottom: '.4rem',
                  letterSpacing: '-.01em',
                }}>
                  {MENTOR.name}
                </h3>
                <p style={{ fontSize: '.9375rem', color: 'rgba(255,255,255,.55)', marginBottom: '1.5rem' }}>
                  {MENTOR.designation}
                </p>
                {MENTOR.paragraphs.map((p, i) => (
                  <p key={i} style={{ fontSize: '.9375rem', color: 'rgba(255,255,255,.75)', lineHeight: 1.75, marginBottom: '1rem' }}>
                    {p}
                  </p>
                ))}
                <p style={{
                  fontFamily: DISPLAY,
                  fontStyle: 'italic',
                  fontSize: '1.05rem',
                  color: 'var(--brass-soft)',
                  lineHeight: 1.6,
                  borderLeft: '2px solid var(--brass)',
                  paddingLeft: '1rem',
                  marginTop: '1.4rem',
                }}>
                  {MENTOR.closing}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Closing ──────────────────────────────────── */}
      <section style={{ padding: '4.5rem 1.5rem', background: 'var(--bg)', textAlign: 'center' }}>
        <div style={{ maxWidth: '560px', margin: '0 auto' }}>
          <h2 style={{
            fontFamily: DISPLAY,
            fontSize: 'clamp(1.3rem, 2.6vw, 1.65rem)',
            fontWeight: 600,
            color: 'var(--navy)',
            marginBottom: '.85rem',
            letterSpacing: '-.01em',
          }}>
            Built to help students find their research fit.
          </h2>
          <p style={{ color: 'var(--muted)', fontSize: '.9375rem', lineHeight: 1.7, marginBottom: '1.75rem' }}>
            Together, this team is working on helping students discover professors,
            research opportunities, and meaningful academic connections.
          </p>
          <Link to="/" style={{
            color: 'var(--navy)',
            fontSize: '.9375rem',
            fontWeight: 600,
            textDecoration: 'none',
            borderBottom: '1px solid var(--brass-soft)',
            paddingBottom: '2px',
          }}>
            ← Back to FindMyProfessor
          </Link>
        </div>
      </section>

      {/* ── Footer (matches Home.jsx, with Team added) ── */}
      <footer style={{
        borderTop: '1px solid var(--line)',
        padding: '1.75rem 1.5rem',
        background: '#fff',
      }}>
        <div style={{
          maxWidth: 'var(--content-max)',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '.75rem',
        }}>
          <div>
            <div style={{
              fontFamily: DISPLAY,
              fontWeight: 600,
              color: 'var(--navy)',
              fontSize: '1rem',
              letterSpacing: '-.01em',
            }}>
              FindMyProfessor
            </div>
            <div style={{ fontSize: '.78rem', color: 'var(--subtle)', marginTop: '.15rem' }}>
              Research discovery &amp; outreach, built for applicants.
            </div>
          </div>
          <nav style={{ display: 'flex', gap: '1.5rem' }}>
            {[['Team', '/team'], ['Privacy', '/privacy'], ['Terms', '/terms'], ['Login', '/login']].map(([label, to]) => (
              <Link key={label} to={to} style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: '.875rem' }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--navy)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>

      <style>{`
        .profile-row {
          display: flex;
          align-items: center;
          gap: 3.25rem;
          margin-bottom: 4.5rem;
        }
        .profile-row:last-child { margin-bottom: 0; }
        .profile-row--reverse { flex-direction: row-reverse; }
        .profile-row-photo {
          flex: 0 0 44%;
          max-width: 44%;
          aspect-ratio: 4 / 5;
          border-radius: var(--r-lg);
          overflow: hidden;
          background: var(--line-light);
          border: 1px solid var(--line);
          box-shadow: var(--shadow-md);
        }
        .profile-row-text { flex: 1 1 56%; min-width: 0; }

        .mentor-panel-inner {
          position: relative;
          display: flex;
          align-items: center;
          gap: 3rem;
          padding: 3rem;
        }
        .mentor-photo {
          flex: 0 0 300px;
          width: 300px;
          aspect-ratio: 1 / 1;
          border-radius: var(--r-lg);
          overflow: hidden;
          border: 3px solid var(--brass);
          box-shadow: 0 0 0 6px rgba(201,164,99,.15);
        }
        .mentor-text { flex: 1 1 auto; min-width: 0; }

        @media (max-width: 820px) {
          .profile-row, .profile-row--reverse {
            flex-direction: column;
            align-items: stretch;
            gap: 1.75rem;
            margin-bottom: 3.5rem;
          }
          .profile-row-photo {
            max-width: 420px;
            width: 100%;
            flex-basis: auto;
            margin: 0 auto;
          }
          .mentor-panel-inner {
            flex-direction: column;
            text-align: center;
            padding: 2.25rem 1.5rem;
            gap: 1.75rem;
          }
          .mentor-photo {
            width: 220px;
            flex-basis: 220px;
            margin: 0 auto;
          }
        }
      `}</style>
    </div>
  );
}
