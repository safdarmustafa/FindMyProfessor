import React from 'react';

function renderEvidenceItem(item) {
  const type = item.evidence_type || item.type;
  const area = item.area || item.research_area || '';

  if (type === 'shared_research_area') {
    return `${area} (from your explicit research interest)`;
  }
  if (type === 'artifact_research_area') {
    const artifact = item.artifact_name || item.artifact || '';
    return `${area} (project "${artifact}")`;
  }
  if (type === 'professor_summary_mentions_area') {
    return `Supporting evidence: professor's research mentions ${area}`;
  }
  if (type === 'university_opportunity') {
    const title = item.opportunity_title || item.title || area;
    return `University opportunity: ${title} (university-wide)`;
  }
  return item.description || item.text || JSON.stringify(item);
}

export default function WhyMatch({ match }) {
  const rm = match?.research_match || {};
  const why = rm.why || [];
  const evidence = rm.evidence || [];

  return (
    <div style={{ fontSize: '.875rem' }}>
      <h4 style={{ fontSize: '.875rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '.6rem' }}>
        Why you're a match
      </h4>
      {why.length > 0 && (
        <ul style={{ paddingLeft: '1.3rem', margin: '0 0 .75rem', color: 'var(--ink-2)' }}>
          {why.map((item, i) => (
            <li key={i} style={{ marginBottom: '.3rem', lineHeight: 1.6 }}>
              {typeof item === 'string' ? item : item.text || JSON.stringify(item)}
            </li>
          ))}
        </ul>
      )}
      {evidence.length > 0 && (
        <>
          <div style={{ fontWeight: 600, color: 'var(--muted)', fontSize: '.75rem', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: '.4rem' }}>
            Evidence
          </div>
          <ul style={{ paddingLeft: '1.3rem', margin: 0, color: 'var(--ink-2)' }}>
            {evidence.map((item, i) => (
              <li key={i} style={{ marginBottom: '.3rem', lineHeight: 1.6, fontSize: '.8125rem' }}>
                {renderEvidenceItem(item)}
              </li>
            ))}
          </ul>
        </>
      )}
      {why.length === 0 && evidence.length === 0 && (
        <p style={{ color: 'var(--muted)', fontStyle: 'italic' }}>No detailed match data available.</p>
      )}
    </div>
  );
}
