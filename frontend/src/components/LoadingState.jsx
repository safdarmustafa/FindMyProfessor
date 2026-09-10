import React from 'react';
import Spinner from './Spinner.jsx';

export default function LoadingState({ message = 'Loading…', fullPage = false }) {
  const style = fullPage
    ? { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: '1rem' }
    : { display: 'flex', alignItems: 'center', gap: '.6rem', padding: '2rem', color: 'var(--muted)', fontSize: '.9rem' };

  return (
    <div style={style}>
      <Spinner size={fullPage ? 32 : 20} />
      <span style={{ color: 'var(--muted)', fontSize: fullPage ? '1rem' : '.875rem' }}>{message}</span>
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ padding: '1.2rem', marginBottom: '.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '.75rem' }}>
        <div>
          <div className="skeleton" style={{ height: '1rem', width: '180px', marginBottom: '.4rem' }} />
          <div className="skeleton" style={{ height: '.75rem', width: '240px' }} />
        </div>
        <div className="skeleton" style={{ height: '2.5rem', width: '3.5rem', borderRadius: 'var(--r-md)' }} />
      </div>
      <div className="skeleton" style={{ height: '.75rem', width: '140px', marginBottom: '.75rem' }} />
      <div className="skeleton" style={{ height: '1.75rem', width: '100%', borderRadius: 'var(--r-sm)' }} />
    </div>
  );
}
