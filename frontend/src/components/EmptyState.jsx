import React from 'react';
import { Link } from 'react-router-dom';

export default function EmptyState({ title, description, action, actionLabel, actionHref }) {
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
        background: 'var(--line-light)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '.5rem',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--subtle)" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
      </div>
      <div>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--ink)', marginBottom: '.35rem' }}>{title}</h3>
        {description && <p style={{ fontSize: '.875rem', color: 'var(--muted)', maxWidth: '360px' }}>{description}</p>}
      </div>
      {actionHref && (
        <Link
          to={actionHref}
          className="btn btn-primary btn-sm"
          style={{ marginTop: '.5rem' }}
        >
          {actionLabel || 'Get started'}
        </Link>
      )}
      {action && !actionHref && (
        <button
          onClick={action}
          className="btn btn-primary btn-sm"
          style={{ marginTop: '.5rem' }}
        >
          {actionLabel || 'Get started'}
        </button>
      )}
    </div>
  );
}
