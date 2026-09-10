import React from 'react';
import { Link } from 'react-router-dom';
import NetworkMotif from '../components/NetworkMotif.jsx';

const DISPLAY = "'Fraunces', Georgia, 'Times New Roman', Times, serif";

const STEPS = [
  { num: '01', label: 'CV Upload', desc: 'Upload your PDF, Word, or text CV' },
  { num: '02', label: 'Research Profile', desc: 'Auto-extracted academic profile' },
  { num: '03', label: 'Professor Discovery', desc: 'Faculty matched to your interests' },
  { num: '04', label: 'Research Match', desc: 'Research alignment scored' },
  { num: '05', label: 'Personalized Outreach', desc: 'AI-drafted emails you review & send' },
];

const FEATURES = [
  {
    icon: (
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2"/>
      </svg>
    ),
    title: 'CV-powered profile',
    desc: 'Upload your CV and we automatically extract research interests, skills, publications, and experience to build a rich academic profile.',
  },
  {
    icon: (
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
    ),
    title: 'Research alignment scoring',
    desc: 'We score research overlap between your profile and faculty based on shared interests, methodology, and publication areas — not just keyword matching.',
  },
  {
    icon: (
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
      </svg>
    ),
    title: 'Personalized email drafts',
    desc: "Generate tailored outreach emails grounded in your actual research background and the professor's specific work. Then review, edit, and send.",
  },
  {
    icon: (
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M4.93 4.93l1.41 1.41M4.93 19.07l1.41-1.41M19.07 19.07l-1.41-1.41M20 12h1M3 12H2M12 20v1M12 3V2"/>
      </svg>
    ),
    title: 'Opportunity discovery',
    desc: 'Discover university-wide research opportunities alongside professor profiles, so you can tailor your outreach to specific programs and openings.',
  },
];

const PROOF_TAGS = ['Computer Vision', 'Deep Learning'];

/* ── The hero's "proof" panel — a static mockup of a real match card ── */
function ProofCard() {
  return (
    <div style={{ position: 'relative', width: '100%', maxWidth: '380px', margin: '0 auto' }}>
      {/* Back card, offset for depth */}
      <div style={{
        position: 'absolute', inset: '14px -10px auto 10px', top: '22px',
        background: 'rgba(255,255,255,.06)',
        border: '1px solid rgba(255,255,255,.14)',
        borderRadius: 'var(--r-lg)',
        height: '92%',
        transform: 'rotate(2.5deg)',
      }} aria-hidden="true" />

      {/* Front card */}
      <div style={{
        position: 'relative',
        background: '#fff',
        borderRadius: 'var(--r-lg)',
        padding: '1.4rem 1.5rem',
        boxShadow: '0 24px 48px rgba(6,10,25,.4), 0 4px 12px rgba(6,10,25,.25)',
        transform: 'rotate(-1.25deg)',
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '.85rem' }}>
          <div>
            <div style={{ fontFamily: DISPLAY, fontWeight: 600, fontSize: '1.05rem', color: 'var(--navy)' }}>
              Dr. Amara Reyes
            </div>
            <div style={{ fontSize: '.78rem', color: 'var(--muted)', marginTop: '.1rem' }}>
              Assoc. Professor · Stanford University
            </div>
          </div>
          <div style={{
            background: 'var(--navy)', color: '#fff', fontWeight: 700, fontSize: '.72rem',
            padding: '.28rem .55rem', borderRadius: 'var(--r-sm)', flexShrink: 0, letterSpacing: '.01em',
          }}>
            94% match
          </div>
        </div>

        <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap', marginBottom: '.95rem' }}>
          {PROOF_TAGS.map(t => (
            <span key={t} style={{
              fontSize: '.7rem', fontWeight: 600, color: 'var(--brass-ink)',
              background: 'var(--brass-bg)', border: '1px solid #ecd8b0',
              padding: '.2rem .55rem', borderRadius: '999px',
            }}>{t}</span>
          ))}
        </div>

        <div style={{
          fontSize: '.78rem', color: 'var(--ink-2, #374151)', lineHeight: 1.6,
          background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 'var(--r-md)',
          padding: '.7rem .8rem', marginBottom: '1rem',
        }}>
          "Your published work on transformer-based vision models directly overlaps with
          Dr. Reyes' current research on…"
        </div>

        <div style={{
          width: '100%', textAlign: 'center', background: 'var(--navy)', color: '#fff',
          fontWeight: 700, fontSize: '.82rem', padding: '.6rem', borderRadius: 'var(--r-md)',
        }}>
          Prepare Email →
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div style={{ minHeight: '100vh', background: '#fff' }}>

      {/* ── Standalone home header ────────────────────── */}
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
          <span style={{
            fontFamily: DISPLAY,
            fontSize: '1.15rem',
            fontWeight: 600,
            color: 'var(--navy)',
            flex: 1,
            letterSpacing: '-.01em',
          }}>
            FindMyProfessor
          </span>
          <nav style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <Link to="/login" style={{
              color: 'var(--muted)',
              fontSize: '.875rem',
              padding: '.35rem .7rem',
              borderRadius: 'var(--r-sm)',
              textDecoration: 'none',
              fontWeight: 500,
              transition: 'color .12s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--navy)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}
            >
              Login
            </Link>
            <Link to="/login" style={{
              background: 'var(--navy)',
              color: '#fff',
              fontSize: '.875rem',
              padding: '.45rem 1.1rem',
              borderRadius: 'var(--r-md)',
              textDecoration: 'none',
              fontWeight: 600,
              boxShadow: '0 1px 2px rgba(26,39,68,.15)',
              transition: 'background .12s, box-shadow .12s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#233260'; e.currentTarget.style.boxShadow = '0 4px 14px rgba(26,39,68,.28)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--navy)'; e.currentTarget.style.boxShadow = '0 1px 2px rgba(26,39,68,.15)'; }}
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────── */}
      <section style={{
        position: 'relative',
        overflow: 'hidden',
        background: 'linear-gradient(160deg, var(--navy-mid) 0%, var(--navy-deep) 100%)',
        padding: '5rem 1.5rem 6rem',
      }}>
        <NetworkMotif opacity={0.55} />
        <div style={{
          position: 'relative',
          maxWidth: 'var(--content-max)',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'minmax(0,1.05fr) minmax(0,.95fr)',
          gap: '3.5rem',
          alignItems: 'center',
        }}
        className="home-hero-grid"
        >
          <div>
            {/* Badge chip */}
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
              marginBottom: '1.75rem',
            }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--brass)' }} />
              Academic Research Platform
            </div>

            <h1 style={{
              fontFamily: DISPLAY,
              fontSize: 'clamp(2.1rem, 4.4vw, 3.35rem)',
              fontWeight: 600,
              color: '#fff',
              lineHeight: 1.14,
              letterSpacing: '-.01em',
              marginBottom: '1.4rem',
              textWrap: 'balance',
            }}>
              Find the <em style={{ fontStyle: 'italic', color: 'var(--brass-soft)', fontWeight: 500 }}>professors</em> behind<br />
              the research you want to pursue.
            </h1>

            <p style={{
              fontSize: '1.05rem',
              color: 'rgba(255,255,255,.6)',
              lineHeight: 1.75,
              marginBottom: '2.25rem',
              maxWidth: '480px',
            }}>
              Upload your CV, get a personalized research profile, and discover faculty
              whose work aligns with yours — then send targeted, evidence-based outreach emails.
            </p>

            <div style={{ display: 'flex', gap: '.85rem', flexWrap: 'wrap', marginBottom: '2.25rem' }}>
              <Link to="/login" style={{
                background: 'var(--brass)',
                color: 'var(--navy-deep)',
                fontWeight: 700,
                fontSize: '.9375rem',
                padding: '.8rem 1.85rem',
                borderRadius: 'var(--r-md)',
                textDecoration: 'none',
                transition: 'transform .15s, box-shadow .15s',
                display: 'inline-flex',
                alignItems: 'center',
                boxShadow: '0 10px 28px -8px rgba(201,164,99,.55)',
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 14px 32px -8px rgba(201,164,99,.7)'; }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 10px 28px -8px rgba(201,164,99,.55)'; }}
              >
                Get Started
              </Link>
              <a href="#how-it-works" style={{
                background: 'transparent',
                color: '#fff',
                fontWeight: 600,
                fontSize: '.9375rem',
                padding: '.8rem 1.75rem',
                borderRadius: 'var(--r-md)',
                textDecoration: 'none',
                border: '1px solid rgba(255,255,255,.28)',
                transition: 'border-color .15s, background .15s',
                display: 'inline-flex',
                alignItems: 'center',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,.55)'; e.currentTarget.style.background = 'rgba(255,255,255,.06)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,.28)'; e.currentTarget.style.background = 'transparent'; }}
              >
                See How It Works
              </a>
            </div>

            <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
              {['CV-powered profiles', 'Evidence-based matching', 'One-click Gmail send'].map(t => (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: '.45rem', fontSize: '.8125rem', color: 'rgba(255,255,255,.55)' }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--brass)" strokeWidth="2.5"><path d="M20 6L9 17l-5-5"/></svg>
                  {t}
                </div>
              ))}
            </div>
          </div>

          <div className="home-hero-proof">
            <ProofCard />
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────── */}
      <section id="how-it-works" style={{
        padding: '5.5rem 1.5rem',
        background: 'var(--bg)',
      }}>
        <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>
          <div style={{ marginBottom: '3rem', maxWidth: '520px' }}>
            <div style={{ fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--brass-ink)', marginBottom: '.6rem' }}>
              The process
            </div>
            <h2 style={{
              fontFamily: DISPLAY,
              fontSize: 'clamp(1.5rem, 3vw, 2rem)',
              fontWeight: 600,
              color: 'var(--navy)',
              marginBottom: '.6rem',
              letterSpacing: '-.01em',
            }}>
              From CV to inbox, in five steps.
            </h2>
            <p style={{ color: 'var(--muted)', fontSize: '.9375rem', lineHeight: 1.65 }}>
              No manual searching through faculty pages — the whole path from your CV
              to a sent, evidence-backed email happens in one place.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '0',
            borderTop: '1px solid var(--line)',
            borderLeft: '1px solid var(--line)',
          }}>
            {STEPS.map((step, i) => (
              <div key={i} style={{
                borderRight: '1px solid var(--line)',
                borderBottom: '1px solid var(--line)',
                background: 'var(--card)',
                padding: '1.75rem 1.4rem',
                position: 'relative',
              }}>
                <div style={{
                  fontFamily: DISPLAY,
                  fontSize: '1.6rem',
                  fontWeight: 600,
                  color: 'var(--brass-ink)',
                  marginBottom: '.9rem',
                  lineHeight: 1,
                }}>{step.num}</div>
                <div style={{ fontWeight: 700, fontSize: '.9rem', color: 'var(--navy)', marginBottom: '.35rem' }}>
                  {step.label}
                </div>
                <div style={{ fontSize: '.8125rem', color: 'var(--muted)', lineHeight: 1.55 }}>
                  {step.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────── */}
      <section style={{ padding: '5.5rem 1.5rem', background: '#fff' }}>
        <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>
          <div style={{ marginBottom: '3rem', maxWidth: '560px' }}>
            <div style={{ fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--brass-ink)', marginBottom: '.6rem' }}>
              What you get
            </div>
            <h2 style={{
              fontFamily: DISPLAY,
              fontSize: 'clamp(1.5rem, 3vw, 2rem)',
              fontWeight: 600,
              color: 'var(--navy)',
              marginBottom: '.6rem',
              letterSpacing: '-.01em',
            }}>
              Built for serious research applicants.
            </h2>
            <p style={{ color: 'var(--muted)', fontSize: '.9375rem', lineHeight: 1.65 }}>
              Every feature designed to help you make a genuine research connection.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '1.25rem',
          }}>
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className="home-feature-card"
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-lg)',
                  padding: '1.6rem',
                  transition: 'transform .18s, box-shadow .18s, border-color .18s',
                }}
              >
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'var(--navy)',
                  color: 'var(--brass-soft)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1.1rem',
                }}>
                  {f.icon}
                </div>
                <h3 style={{ fontFamily: DISPLAY, fontSize: '1.02rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '.45rem' }}>
                  {f.title}
                </h3>
                <p style={{ fontSize: '.875rem', color: 'var(--muted)', lineHeight: 1.7 }}>
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ───────────────────────────────── */}
      <section style={{
        position: 'relative',
        overflow: 'hidden',
        background: 'linear-gradient(160deg, var(--navy-mid) 0%, var(--navy-deep) 100%)',
        padding: '5.5rem 1.5rem',
        textAlign: 'center',
      }}>
        <NetworkMotif opacity={0.32} />
        <div style={{ position: 'relative', maxWidth: '540px', margin: '0 auto' }}>
          <h2 style={{
            fontFamily: DISPLAY,
            fontSize: 'clamp(1.6rem, 3vw, 2.15rem)',
            fontWeight: 600,
            color: '#fff',
            marginBottom: '.85rem',
            letterSpacing: '-.01em',
          }}>
            Ready to find your research fit?
          </h2>
          <p style={{
            color: 'rgba(255,255,255,.55)',
            marginBottom: '2.1rem',
            fontSize: '.9375rem',
            lineHeight: 1.65,
          }}>
            Upload your CV and get matched with faculty in minutes.
          </p>
          <Link to="/login" style={{
            background: 'var(--brass)',
            color: 'var(--navy-deep)',
            fontWeight: 700,
            fontSize: '1rem',
            padding: '.9rem 2.1rem',
            borderRadius: 'var(--r-md)',
            textDecoration: 'none',
            display: 'inline-flex',
            alignItems: 'center',
            boxShadow: '0 10px 28px -8px rgba(201,164,99,.55)',
            transition: 'transform .15s, box-shadow .15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 14px 32px -8px rgba(201,164,99,.7)'; }}
          onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 10px 28px -8px rgba(201,164,99,.55)'; }}
          >
            Get Started — It's Free
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────── */}
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
            {[['Privacy', '/privacy'], ['Terms', '/terms'], ['Login', '/login']].map(([label, to]) => (
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
        .home-feature-card:hover {
          transform: translateY(-3px);
          box-shadow: var(--shadow-md);
          border-color: var(--brass-soft);
        }
        @media (max-width: 860px) {
          .home-hero-grid { grid-template-columns: 1fr !important; }
          .home-hero-proof { display: none; }
        }
      `}</style>
    </div>
  );
}
