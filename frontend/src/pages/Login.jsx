import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';
import NetworkMotif from '../components/NetworkMotif.jsx';

const DISPLAY = "'Fraunces', Georgia, 'Times New Roman', Times, serif";

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="10" width="16" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

const TRUST_POINTS = [
  { title: 'Research-aligned matching', desc: 'Faculty ranked by genuine overlap with your work — not keyword search.' },
  { title: 'Evidence-based outreach', desc: 'Every drafted email cites the specific research it references.' },
  { title: 'Direct Gmail integration', desc: 'Send from your own inbox — we never see your other mail.' },
];

export default function Login() {
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
      if (session) {
        navigate('/onboarding', { replace: true });
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setSession(session);
      if (event === 'SIGNED_IN') {
        navigate('/onboarding', { replace: true });
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  const handleGoogleSignIn = async () => {
    setSigningIn(true);
    setError(null);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: (import.meta.env.VITE_SITE_URL || 'http://localhost:5173') + '/login' },
      });
      if (error) throw error;
    } catch (e) {
      setError(e.message || 'Sign in failed. Please try again.');
      setSigningIn(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setSession(null);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>

      {/* ── Left panel ───────────────────────────────── */}
      <div
        className="login-left-panel"
        style={{
          position: 'relative',
          overflow: 'hidden',
          width: '46%',
          background: 'linear-gradient(160deg, var(--navy-mid) 0%, var(--navy-deep) 100%)',
          padding: '3.5rem',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <NetworkMotif opacity={0.55} />

        <Link to="/" style={{
          position: 'relative',
          fontFamily: DISPLAY,
          fontSize: '1.15rem',
          fontWeight: 600,
          color: '#fff',
          textDecoration: 'none',
          letterSpacing: '-.01em',
        }}>
          FindMyProfessor
        </Link>

        <div style={{ position: 'relative' }}>
          <div style={{
            width: '30px', height: '2px', background: 'var(--brass)', marginBottom: '1.4rem',
          }} />
          <h1 style={{
            fontFamily: DISPLAY,
            fontSize: 'clamp(1.5rem, 2.6vw, 2.05rem)',
            color: '#fff',
            fontWeight: 500,
            fontStyle: 'italic',
            lineHeight: 1.3,
            marginBottom: '2.25rem',
            maxWidth: '420px',
          }}>
            "Your next research opportunity may start with one professor."
          </h1>

          {/* Trust points */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
            {TRUST_POINTS.map((point, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '.75rem' }}>
                <div style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  background: 'rgba(201,164,99,.15)',
                  border: '1px solid rgba(201,164,99,.5)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  marginTop: '.1rem',
                }}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--brass)" strokeWidth="3">
                    <path d="M20 6L9 17l-5-5"/>
                  </svg>
                </div>
                <div>
                  <div style={{ color: '#fff', fontSize: '.875rem', fontWeight: 600, marginBottom: '.15rem' }}>
                    {point.title}
                  </div>
                  <div style={{ color: 'rgba(255,255,255,.5)', fontSize: '.8125rem', lineHeight: 1.55 }}>
                    {point.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ position: 'relative', fontSize: '.75rem', color: 'rgba(255,255,255,.35)' }}>
          © {new Date().getFullYear()} FindMyProfessor
        </div>
      </div>

      {/* ── Right panel ──────────────────────────────── */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        padding: '3rem 2rem',
      }}>
        <div style={{
          width: '100%',
          maxWidth: '380px',
          background: '#fff',
          border: '1px solid var(--line)',
          borderRadius: 'var(--r-xl)',
          boxShadow: '0 1px 2px rgba(15,23,42,.04), 0 20px 44px -18px rgba(15,23,42,.16)',
          padding: '2.5rem 2.25rem',
        }}>
          {/* Logo */}
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{
              fontFamily: DISPLAY,
              fontSize: '1.35rem',
              fontWeight: 600,
              color: 'var(--navy)',
              marginBottom: '.4rem',
              letterSpacing: '-.01em',
            }}>
              Welcome back
            </div>
            <p style={{ fontSize: '.875rem', color: 'var(--muted)', margin: 0 }}>
              Sign in to continue your research search.
            </p>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', color: 'var(--muted)', padding: '2rem', fontSize: '.875rem' }}>
              Loading…
            </div>
          ) : session ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{
                padding: '.8rem 1rem',
                background: 'var(--green-bg)',
                border: '1px solid var(--green-bdr)',
                borderRadius: 'var(--r-md)',
                fontSize: '.875rem',
                color: 'var(--green)',
                marginBottom: '1.25rem',
                fontWeight: 500,
              }}>
                Signed in as {session.user?.email}
              </div>
              <Link
                to="/matches"
                style={{
                  display: 'block',
                  textAlign: 'center',
                  width: '100%',
                  marginBottom: '.75rem',
                  padding: '.75rem 1rem',
                  background: 'var(--navy)',
                  color: '#fff',
                  borderRadius: 'var(--r-md)',
                  textDecoration: 'none',
                  fontWeight: 700,
                  fontSize: '.9375rem',
                }}
              >
                Continue to app →
              </Link>
              <button
                onClick={handleSignOut}
                style={{
                  width: '100%',
                  padding: '.65rem 1rem',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--muted)',
                  fontSize: '.875rem',
                  cursor: 'pointer',
                  borderRadius: 'var(--r-md)',
                }}
              >
                Sign out
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={handleGoogleSignIn}
                disabled={signingIn}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '.65rem',
                  padding: '.85rem 1rem',
                  background: '#fff',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-md)',
                  fontSize: '.9375rem',
                  fontWeight: 600,
                  color: 'var(--ink)',
                  cursor: signingIn ? 'not-allowed' : 'pointer',
                  boxShadow: 'var(--shadow-sm)',
                  transition: 'box-shadow .15s, border-color .15s, transform .15s',
                  opacity: signingIn ? .7 : 1,
                }}
                onMouseEnter={e => { if (!signingIn) { e.currentTarget.style.boxShadow = 'var(--shadow-md)'; e.currentTarget.style.borderColor = 'var(--subtle)'; e.currentTarget.style.transform = 'translateY(-1px)'; } }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; e.currentTarget.style.borderColor = 'var(--line)'; e.currentTarget.style.transform = 'translateY(0)'; }}
              >
                <GoogleIcon />
                {signingIn ? 'Redirecting…' : 'Continue with Google'}
              </button>

              {error && (
                <p style={{ color: 'var(--red)', fontSize: '.8125rem', textAlign: 'center', marginTop: '.75rem', margin: '.75rem 0 0' }}>
                  {error}
                </p>
              )}

              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '.5rem',
                marginTop: '1.5rem',
                padding: '.75rem .85rem',
                background: 'var(--bg)',
                border: '1px solid var(--line)',
                borderRadius: 'var(--r-md)',
              }}>
                <span style={{ color: 'var(--muted)', flexShrink: 0, marginTop: '.15rem' }}>
                  <LockIcon />
                </span>
                <p style={{ fontSize: '.78rem', color: 'var(--muted)', lineHeight: 1.55, margin: 0 }}>
                  Google Sign-In only confirms your identity. We'll ask separately,
                  and only when you choose to, before connecting Gmail to send outreach.
                </p>
              </div>

              <p style={{
                fontSize: '.75rem',
                color: 'var(--subtle)',
                textAlign: 'center',
                marginTop: '1.5rem',
                lineHeight: 1.65,
              }}>
                By continuing, you agree to our{' '}
                <Link to="/terms" style={{ color: 'var(--muted)', textDecoration: 'underline' }}>Terms</Link>
                {' '}and{' '}
                <Link to="/privacy" style={{ color: 'var(--muted)', textDecoration: 'underline' }}>Privacy Policy</Link>.
              </p>
            </>
          )}
        </div>

        <Link to="/" style={{
          marginTop: '1.5rem',
          fontSize: '.8125rem',
          color: 'var(--muted)',
          textDecoration: 'none',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '.3rem',
        }}
        onMouseEnter={e => e.currentTarget.style.color = 'var(--navy)'}
        onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}
        >
          ← Back to home
        </Link>
      </div>

      <style>{`
        @media (max-width: 700px) {
          .login-left-panel { display: none !important; }
        }
      `}</style>
    </div>
  );
}
