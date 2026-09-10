import React from 'react';

export default function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '4rem 2rem',
      textAlign: 'center',
      gap: '1rem',
    }}>
      <div style={{
        width: '52px',
        height: '52px',
        borderRadius: '50%',
        background: 'var(--red-bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
        </svg>
      </div>
      <div>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--ink)', marginBottom: '.35rem' }}>{title}</h3>
        {message && <p style={{ fontSize: '.875rem', color: 'var(--muted)', maxWidth: '380px' }}>{message}</p>}
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn btn-secondary btn-sm" style={{ marginTop: '.5rem' }}>
          Try again
        </button>
      )}
    </div>
  );
}
