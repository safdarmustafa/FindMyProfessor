import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Privacy() {
  const loc = useLocation();
  return (
    <div className="doc-layout">
      <header className="doc-header">
        <div className="doc-header-inner">
          <Link to="/" className="doc-brand">FindMyProfessor</Link>
          <nav className="doc-nav">
            <Link to="/">Home</Link>
            <Link to="/privacy" className={loc.pathname === '/privacy' ? 'active' : ''}>Privacy</Link>
            <Link to="/terms" className={loc.pathname === '/terms' ? 'active' : ''}>Terms</Link>
            <Link to="/login">Login</Link>
          </nav>
        </div>
      </header>

      <main className="doc-body">
        <h1>Privacy Policy</h1>
        <p className="last-updated">Last updated: September 2026</p>

        <p>
          This Privacy Policy describes how FindMyProfessor ("we", "us", or "our") collects,
          uses, and handles information when you use the FindMyProfessor platform
          (findmyprofessor.online). Please read it carefully. By using FindMyProfessor
          you acknowledge this policy.
        </p>

        <h2>1. Account Authentication</h2>
        <p>
          You can sign in to FindMyProfessor using your Google account through{' '}
          <a href="https://supabase.com" target="_blank" rel="noopener">Supabase Auth</a>.
          When you sign in with Google, we receive authentication information — including
          your Google account email address — sufficient to create and maintain your
          FindMyProfessor account and session. We do not receive your Google account password.
        </p>

        <h2>2. CV and Resume Data</h2>
        <p>
          You may upload a CV or resume to FindMyProfessor. Your uploaded CV is processed
          server-side to extract relevant profile information used for professor and research
          matching. This extracted information may include:
        </p>
        <ul>
          <li>Name and contact information (if present in your CV)</li>
          <li>Education history</li>
          <li>Research interests and areas</li>
          <li>Skills and technical abilities</li>
          <li>Projects, publications, or research experience</li>
          <li>Work experience</li>
        </ul>
        <p>
          Your CV file and extracted profile data are stored in association with your account
          and are used to provide the matching and outreach features of FindMyProfessor.
          We do not sell or share your CV data with third parties for marketing purposes.
        </p>

        <h2>3. Professor and Research Matching</h2>
        <p>
          Information extracted from your CV and profile is used to identify potentially
          relevant professors, labs, research areas, and opportunities within FindMyProfessor's
          database. Matching is performed server-side. Professor and research information
          displayed in FindMyProfessor is sourced from publicly available academic information.
        </p>

        <h2>4. Email Drafts and Outreach History</h2>
        <p>
          FindMyProfessor can generate personalized outreach email drafts based on your
          profile, a selected professor, relevant research information, and a selected
          opportunity where applicable. These drafts may be stored as part of your outreach
          history within your account so you can review and track them.
        </p>
        <p>
          Draft email content is associated with your account and is not shared with
          third parties.
        </p>

        <h2>5. Gmail Integration</h2>
        <p>
          You may optionally connect your Gmail account to FindMyProfessor. The Gmail
          integration uses Google's Gmail API with the following OAuth scope:
        </p>
        <ul>
          <li><code>https://www.googleapis.com/auth/gmail.send</code></li>
        </ul>
        <p>
          This scope grants FindMyProfessor permission to send email on your behalf through
          your connected Gmail account. Specifically:
        </p>
        <ul>
          <li>
            <strong>Email sending is always explicit.</strong> FindMyProfessor only sends an
            email when you review the draft and actively choose to send it. We do not
            send emails automatically or in bulk.
          </li>
          <li>
            <strong>We do not read your Gmail inbox.</strong> The <code>gmail.send</code>
            scope does not grant access to your inbox, existing messages, contacts,
            or any other Gmail data.
          </li>
          <li>
            <strong>Token storage.</strong> Gmail OAuth tokens (access token and refresh
            token) are stored server-side and encrypted at rest. They are never exposed to
            the browser or third parties.
          </li>
          <li>
            <strong>Revoking access.</strong> You can disconnect Gmail from within
            FindMyProfessor at any time. You can also revoke access directly from your{' '}
            <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener">
              Google Account permissions
            </a> page.
          </li>
        </ul>

        <h2>6. Third-Party Services</h2>
        <p>FindMyProfessor currently uses the following third-party services:</p>
        <ul>
          <li>
            <strong>Supabase</strong> — for authentication, session management, and database
            storage. See <a href="https://supabase.com/privacy" target="_blank" rel="noopener">Supabase's Privacy Policy</a>.
          </li>
          <li>
            <strong>Google APIs</strong> — for Google Sign-In (via Supabase Auth) and Gmail
            sending. See <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Google's Privacy Policy</a>.
          </li>
        </ul>
        <p>
          We do not use advertising networks, analytics tracking pixels, or sell data
          to third parties.
        </p>

        <h2>7. Data Security</h2>
        <p>
          We take reasonable steps to protect your information, including:
        </p>
        <ul>
          <li>Authentication and session controls to restrict access to your account data</li>
          <li>Server-side handling of sensitive OAuth tokens — tokens are never sent to the browser</li>
          <li>Encryption of stored Gmail OAuth tokens at rest</li>
          <li>Access controls intended to keep each user's data separated from others</li>
        </ul>
        <p>
          No system can guarantee absolute security. We encourage you to use a strong
          password for your Google account and to revoke access you no longer need.
        </p>

        <h2>8. Data Retention and Deletion</h2>
        <p>
          Your account data, CV files, extracted profile, email drafts, and Gmail connection
          are retained while your account is active. If you would like your data deleted,
          please contact us at the email below. We will process deletion requests in a
          reasonable time frame.
        </p>
        <p>
          You can disconnect Gmail at any time from within the application without deleting
          your account.
        </p>

        <h2>9. Children's Privacy</h2>
        <p>
          FindMyProfessor is intended for use by students and adults. We do not knowingly
          collect personal information from children under the age of 13. If you believe
          a child under 13 has provided us with personal information, please contact us
          and we will promptly remove it.
        </p>

        <h2>10. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. When we do, the updated
          version will be posted on this page with a revised "Last updated" date. We
          encourage you to review this page periodically.
        </p>

        <h2>11. Contact</h2>
        <p>
          If you have questions about this Privacy Policy or wish to make a privacy or
          data deletion request, please contact:
        </p>
        <p>
          <a href="mailto:safdarmustafa01@gmail.com">safdarmustafa01@gmail.com</a>
        </p>
      </main>

      <footer className="doc-footer">
        <div className="doc-footer-inner">
          <span>FindMyProfessor</span>
          <nav className="footer-links">
            <Link to="/">Home</Link>
            <Link to="/privacy" style={{ marginLeft: '1.25rem' }}>Privacy</Link>
            <Link to="/terms" style={{ marginLeft: '1.25rem' }}>Terms</Link>
            <Link to="/login" style={{ marginLeft: '1.25rem' }}>Login</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
