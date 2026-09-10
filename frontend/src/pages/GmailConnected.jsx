import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { getPendingIntent } from '../services/gmail.js';
import Spinner from '../components/Spinner.jsx';

export default function GmailConnected() {
  const navigate = useNavigate();

  // getPendingIntent() only reads localStorage — safe to call more than once,
  // including React 18 StrictMode's double-invoke of a lazy useState
  // initialiser in development.
  //
  // This page deliberately does NOT clear the pending intent. The compose
  // page it hands off to (EmailCompose) needs the intent's draft_id to
  // restore the in-progress draft, and is the sole owner of clearing it —
  // if this page cleared it first, the compose page would find it already
  // gone by the time it mounts.
  const [returnPath] = useState(() => getPendingIntent()?.return_path ?? null);

  const redirecting = returnPath !== null;

  useEffect(() => {
    // Popup window flow — notify the opener tab and close this one.
    if (window.opener && !window.opener.closed) {
      try {
        window.opener.postMessage({ type: 'gmail_connected' }, window.location.origin);
      } catch {}
      window.close();
      return;
    }

    const destination = returnPath || '/outreach/history';
    const delay = returnPath ? 1500 : 2000;

    const timer = setTimeout(() => {
      navigate(destination, { replace: true });
    }, delay);

    return () => clearTimeout(timer);
  }, [navigate, returnPath]);

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    }}>
      <div style={{
        background: 'var(--card)',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-xl)',
        maxWidth: '440px',
        width: '100%',
        padding: '2.75rem',
        textAlign: 'center',
        boxShadow: 'var(--shadow-md)',
      }}>
        {/* Large green checkmark circle */}
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'var(--green-bg)',
          border: '2px solid var(--green-bdr)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.5rem',
        }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2.5">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
        </div>

        {redirecting ? (
          <>
            <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '.5rem', fontFamily: 'var(--font-serif)' }}>
              Gmail Connected!
            </h1>
            <p style={{ fontSize: '.875rem', color: 'var(--muted)', marginBottom: '1.5rem', lineHeight: 1.6 }}>
              Returning to your draft…
            </p>
            <Spinner size={28} />
          </>
        ) : (
          <>
            <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '.5rem', fontFamily: 'var(--font-serif)' }}>
              Gmail Connected!
            </h1>
            <p style={{ fontSize: '.875rem', color: 'var(--muted)', marginBottom: '1.75rem', lineHeight: 1.6 }}>
              Your Gmail account is now connected to FindMyProfessor. You can send
              personalized emails directly from the platform.
            </p>
            <Link to="/matches" style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '.4rem',
              background: 'var(--navy)',
              color: '#fff',
              padding: '.7rem 1.5rem',
              borderRadius: 'var(--r-md)',
              textDecoration: 'none',
              fontWeight: 700,
              fontSize: '.9375rem',
            }}>
              Continue to Matches
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
