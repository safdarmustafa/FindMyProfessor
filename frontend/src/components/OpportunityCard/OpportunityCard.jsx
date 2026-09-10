import React from 'react';

export default function OpportunityCard({ opportunity, isUniversityWide = true }) {
  const title = opportunity?.title || opportunity?.opportunity_type || 'Opportunity';
  const status = opportunity?.status || opportunity?.opportunity_status || '';
  const deadline = opportunity?.deadline || opportunity?.application_deadline || '';
  const description = opportunity?.description || '';
  const url = opportunity?.url || opportunity?.application_url || '';

  const statusColor = {
    open: { background: 'var(--green-bg)', color: 'var(--green)', border: '1px solid var(--green-bdr)' },
    rolling: { background: 'var(--accent-bg)', color: 'var(--accent)', border: '1px solid var(--accent-bdr)' },
    closed: { background: 'var(--line-light)', color: 'var(--muted)', border: '1px solid var(--line)' },
  }[status?.toLowerCase()] || { background: 'var(--line-light)', color: 'var(--muted)', border: '1px solid var(--line)' };

  return (
    <div style={{
      border: '1px solid var(--line)',
      borderRadius: 'var(--r-md)',
      padding: '.75rem 1rem',
      background: 'var(--card)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '.5rem', marginBottom: '.3rem' }}>
        <div style={{ fontSize: '.875rem', fontWeight: 600, color: 'var(--ink)' }}>
          {title}
          {isUniversityWide && (
            <span style={{ marginLeft: '.5rem', fontSize: '.7rem', color: 'var(--muted)', fontWeight: 500, background: 'var(--line-light)', padding: '.1rem .35rem', borderRadius: 'var(--r-xs)', border: '1px solid var(--line)' }}>
              university-wide
            </span>
          )}
        </div>
        {status && (
          <span style={{ fontSize: '.7rem', fontWeight: 600, borderRadius: 'var(--r-xs)', padding: '.15rem .4rem', whiteSpace: 'nowrap', ...statusColor }}>
            {status}
          </span>
        )}
      </div>
      {description && <p style={{ fontSize: '.8125rem', color: 'var(--muted)', margin: '.25rem 0', lineHeight: 1.5 }}>{description}</p>}
      {deadline && <p style={{ fontSize: '.75rem', color: 'var(--subtle)', margin: '.25rem 0' }}>Deadline: {deadline}</p>}
      {url && (
        <a href={url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '.8125rem', color: 'var(--accent)' }}>
          View opportunity →
        </a>
      )}
    </div>
  );
}
