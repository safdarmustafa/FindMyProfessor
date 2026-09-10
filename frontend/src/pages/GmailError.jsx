import React from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { gmailConnectUrl } from '../services/gmail.js';
import { getProfileId } from '../services/api.js';

const REASON_COPY = {
  denied: 'Access was denied. Allow Gmail send permission and try again.',
  missing_params: 'The OAuth callback was missing required parameters.',
  invalid_state: 'The OAuth session expired or was invalid. Please try again.',
  exchange_failed: 'Could not complete the Google token exchange.',
  no_token: 'Google did not return an access token.',
  store_failed: 'Could not save the Gmail connection.',
};

export default function GmailError() {
  const profileId = getProfileId();
  const [params] = useSearchParams();
  const reason = params.get('reason');
  const reasonText = REASON_COPY[reason] || (reason ? `Connection failed (${reason}).` : null);

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
        {/* Red X icon */}
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'var(--red-bg)',
          border: '2px solid #fecaca',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.5rem',
        }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M15 9l-6 6M9 9l6 6"/>
          </svg>
        </div>

        <h1 style={{
          fontSize: '1.3rem',
          fontWeight: 700,
          color: 'var(--navy)',
          marginBottom: '.5rem',
          fontFamily: 'var(--font-serif)',
        }}>
          Gmail Connection Failed
        </h1>
        <p style={{
          fontSize: '.875rem',
          color: 'var(--muted)',
          marginBottom: '2rem',
          lineHeight: 1.65,
        }}>
          {reasonText || 'Something went wrong while connecting your Gmail account. Please try again. If the problem persists, make sure you allow the required permissions.'}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
          {profileId && (
            <a
              href={gmailConnectUrl(profileId)}
              style={{
                display: 'block',
                padding: '.7rem 1.5rem',
                background: 'var(--navy)',
                color: '#fff',
                borderRadius: 'var(--r-md)',
                textDecoration: 'none',
                fontWeight: 700,
                fontSize: '.9375rem',
                textAlign: 'center',
              }}
            >
              Try Again
            </a>
          )}
          <Link
            to="/matches"
            style={{
              display: 'block',
              padding: '.65rem 1.25rem',
              background: 'var(--card)',
              color: 'var(--ink)',
              border: '1px solid var(--line)',
              borderRadius: 'var(--r-md)',
              textDecoration: 'none',
              fontWeight: 500,
              fontSize: '.875rem',
              textAlign: 'center',
            }}
          >
            Back to App
          </Link>
        </div>
      </div>
    </div>
  );
}
