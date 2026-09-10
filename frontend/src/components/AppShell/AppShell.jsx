import React, { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useGmailStatus } from '../../hooks/useGmailStatus.js';
import { useAuth } from '../../hooks/useAuth.js';
import './AppShell.css';

function initialsFor(email) {
  if (!email) return '?';
  return email.trim()[0].toUpperCase();
}

function AccountMenu({ user, signOut }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  if (!user) {
    return (
      <Link to="/login" className="app-nav-signin">Sign in</Link>
    );
  }

  const email = user.email || '';

  const handleSignOut = async () => {
    setOpen(false);
    await signOut();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app-account-menu" ref={rootRef}>
      <button
        type="button"
        className="app-account-avatar"
        onClick={() => setOpen(v => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="Account menu"
        title={email}
      >
        {initialsFor(email)}
      </button>
      {open && (
        <div className="app-account-dropdown" role="menu">
          <div className="app-account-email" title={email}>{email}</div>
          <Link to="/onboarding" className="app-account-item" role="menuitem" onClick={() => setOpen(false)}>
            Change CV
          </Link>
          <button type="button" className="app-account-item app-account-item--danger" role="menuitem" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export default function AppShell({ children }) {
  const { status } = useGmailStatus();
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const isConnected = status?.connected === true;
  const gmailLabel = isConnected ? (status.email || 'Gmail connected') : null;

  const handleMobileSignOut = async () => {
    setMenuOpen(false);
    await signOut();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app-shell">
      <header className="app-nav">
        <div className="app-nav-inner">
          <Link to="/" className="app-nav-brand">FindMyProfessor</Link>

          <nav className="app-nav-links">
            <NavLink
              to="/matches"
              className={({ isActive }) => 'app-nav-link' + (isActive ? ' active' : '')}
            >
              Research Matches
            </NavLink>
            <NavLink
              to="/onboarding"
              className={({ isActive }) => 'app-nav-link' + (isActive ? ' active' : '')}
            >
              My CV
            </NavLink>
            <NavLink
              to="/outreach/history"
              className={({ isActive }) => 'app-nav-link' + (isActive ? ' active' : '')}
            >
              Outreach
            </NavLink>
          </nav>

          <div className="app-nav-right">
            {isConnected ? (
              <div className="app-nav-gmail">
                <span className="status-dot green" />
                <span className="app-nav-gmail-label">{gmailLabel}</span>
              </div>
            ) : (
              <div className="app-nav-gmail app-nav-gmail--disconnected">
                <span className="status-dot grey" />
                <Link to="/matches" className="app-nav-gmail-connect">Connect Gmail</Link>
              </div>
            )}
            <span className="app-nav-divider" aria-hidden="true" />
            <AccountMenu user={user} signOut={signOut} />
          </div>

          <button
            className="app-nav-hamburger"
            onClick={() => setMenuOpen(v => !v)}
            aria-label="Toggle menu"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {menuOpen
                ? <path d="M18 6L6 18M6 6l12 12"/>
                : <path d="M3 12h18M3 6h18M3 18h18"/>
              }
            </svg>
          </button>
        </div>

        {menuOpen && (
          <div className="app-nav-mobile-menu">
            <NavLink to="/matches" className="app-nav-mobile-link" onClick={() => setMenuOpen(false)}>
              Research Matches
            </NavLink>
            <NavLink to="/onboarding" className="app-nav-mobile-link" onClick={() => setMenuOpen(false)}>
              My CV
            </NavLink>
            <NavLink to="/outreach/history" className="app-nav-mobile-link" onClick={() => setMenuOpen(false)}>
              Outreach History
            </NavLink>
            {isConnected && (
              <div className="app-nav-mobile-gmail">
                <span className="status-dot green" />
                <span>{gmailLabel}</span>
              </div>
            )}
            {user ? (
              <>
                <div className="app-nav-mobile-email">{user.email}</div>
                <button type="button" className="app-nav-mobile-link app-nav-mobile-signout" onClick={handleMobileSignOut}>
                  Sign out
                </button>
              </>
            ) : (
              <Link to="/login" className="app-nav-mobile-link" onClick={() => setMenuOpen(false)}>
                Sign in
              </Link>
            )}
          </div>
        )}
      </header>

      <main className="app-main">
        {children}
      </main>
    </div>
  );
}
