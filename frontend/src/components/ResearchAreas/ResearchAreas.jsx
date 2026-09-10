import React from 'react';

export default function ResearchAreas({ areas, label = true }) {
  if (!areas || areas.length === 0) return null;

  const areaList = Array.isArray(areas) ? areas : [areas];
  const display = areaList.map(a => typeof a === 'string' ? a : a.area || a.name || String(a)).filter(Boolean);

  return (
    <div style={{
      background: 'var(--line-light)',
      borderRadius: 'var(--r-sm)',
      padding: '.35rem .65rem',
      fontSize: '.8125rem',
      color: 'var(--ink-2)',
      lineHeight: 1.5,
    }}>
      {label && (
        <span style={{
          fontWeight: 600,
          color: 'var(--muted)',
          marginRight: '.4rem',
          fontSize: '.75rem',
          textTransform: 'uppercase',
          letterSpacing: '.04em',
        }}>Research</span>
      )}
      {display.join(' · ')}
    </div>
  );
}
