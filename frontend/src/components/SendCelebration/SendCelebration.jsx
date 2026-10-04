import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './SendCelebration.css';

function Sparkle({ style }) {
  return (
    <svg className="sparkle" style={style} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 0l2.4 8.6L24 12l-9.6 3.4L12 24l-2.4-8.6L0 12l9.6-3.4z" />
    </svg>
  );
}

function PaperPlaneIcon({ size = 40, color = '#fff' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 2L11 13" />
      <path d="M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  );
}

const SPARKLES = [
  { top: '-16px', left: '14%', '--delay': '0s' },
  { top: '16%', right: '-12px', '--delay': '.7s' },
  { bottom: '24%', left: '-12px', '--delay': '1.3s' },
  { bottom: '-12px', right: '20%', '--delay': '1.9s' },
];

/**
 * Confirmation after a successful send. Professional rather than festive:
 * sending an email is a step, not an outcome. A paper plane takes off, the
 * card confirms what was sent, and offers the sensible next steps.
 */
export default function SendCelebration({ professorName, toAddress, cvName, sentAt, onClose }) {
  const closeRef = useRef(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const sentTime = sentAt ? new Date(sentAt) : null;
  const sentLabel = sentTime && !Number.isNaN(sentTime.getTime())
    ? sentTime.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
    : null;

  return (
    <div
      className="celebrate-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="celebrate-title"
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      <svg className="plane-trail" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <path d="M-4 82 Q 45 62 104 6" vectorEffect="non-scaling-stroke" />
      </svg>
      <span className="paper-plane" aria-hidden="true"><PaperPlaneIcon size={54} /></span>

      <div className="celebrate-card">
        {SPARKLES.map((s, i) => <Sparkle key={i} style={s} />)}

        <div className="celebrate-badge" aria-hidden="true">
          <PaperPlaneIcon size={38} />
          <span className="badge-check">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.2"
              strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
          </span>
        </div>

        <h2 id="celebrate-title" className="celebrate-title">Email sent successfully</h2>
        <p className="celebrate-subtitle">
          Your outreach email to <strong>{professorName}</strong> has been sent from your Gmail account.
        </p>

        {(toAddress || cvName || sentLabel) && (
          <div className="celebrate-details">
            {toAddress && <div><span>To</span><span>{toAddress}</span></div>}
            {cvName && <div><span>CV</span><span>{cvName} attached</span></div>}
            {sentLabel && <div><span>Sent</span><span>{sentLabel}</span></div>}
          </div>
        )}

        <div className="celebrate-actions">
          <Link to="/outreach/history" className="celebrate-primary">View in Outreach History</Link>
          <Link to="/matches" className="celebrate-secondary">Find more professors</Link>
          <button ref={closeRef} type="button" className="celebrate-close" onClick={onClose}>Close</button>
        </div>

        <p className="celebrate-note">
          Professors usually reply within one to two weeks. If you don't hear back, a polite follow-up after 10–14 days is perfectly normal.
        </p>
      </div>
    </div>
  );
}
