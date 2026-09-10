import React from 'react';

// Determines alignment label from score/priority
export function getAlignmentLabel(score, priority) {
  if (score >= 80 || priority === 'high') return 'strong';
  if (score >= 60 || priority === 'medium') return 'good';
  return 'potential';
}

export function getAlignmentText(level) {
  if (level === 'strong') return 'Strong research alignment';
  if (level === 'good') return 'Good research alignment';
  return 'Potential research alignment';
}

export function getAlignmentClass(level) {
  if (level === 'strong') return 'badge badge-green';
  if (level === 'good') return 'badge badge-blue';
  return 'badge badge-grey';
}

export default function StatusBadge({ status }) {
  // status: 'draft' | 'ready' | 'sending' | 'sent' | 'failed'
  const map = {
    draft: { label: 'Draft', cls: 'badge badge-grey' },
    ready: { label: 'Ready', cls: 'badge badge-blue' },
    sending: { label: 'Sending', cls: 'badge badge-amber' },
    sent: { label: 'Sent', cls: 'badge badge-green' },
    failed: { label: 'Failed', cls: 'badge badge-red' },
  };
  const { label, cls } = map[status] || { label: status, cls: 'badge badge-grey' };
  return <span className={cls}>{label}</span>;
}
