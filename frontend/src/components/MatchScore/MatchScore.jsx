import React from 'react';
import { getAlignmentLabel, getAlignmentText, getAlignmentClass } from '../StatusBadge/StatusBadge.jsx';

export default function MatchScore({ score, priority, compact = false }) {
  const level = getAlignmentLabel(score, priority);
  const text = getAlignmentText(level);
  const badgeClass = getAlignmentClass(level);

  if (compact) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '.2rem' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '.1rem' }}>
          <span style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '1.4rem',
            fontWeight: 700,
            color: 'var(--navy)',
            lineHeight: 1,
          }}>{score}</span>
          <span style={{ fontSize: '.7rem', color: 'var(--muted)', fontWeight: 500 }}>%</span>
        </div>
        <span className={badgeClass} style={{ fontSize: '.68rem', padding: '.1rem .35rem' }}>
          {level === 'strong' ? 'Strong' : level === 'good' ? 'Good' : 'Potential'}
        </span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '.3rem' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '.15rem' }}>
        <span style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '2rem',
          fontWeight: 700,
          color: 'var(--navy)',
          lineHeight: 1,
        }}>{score}</span>
        <span style={{ fontSize: '.8rem', color: 'var(--muted)' }}>%</span>
      </div>
      <span style={{ fontSize: '.75rem', color: 'var(--muted)', fontWeight: 500 }}>Research Match</span>
      <span className={badgeClass}>{text}</span>
    </div>
  );
}
