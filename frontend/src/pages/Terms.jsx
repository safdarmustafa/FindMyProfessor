import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Terms() {
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
        <h1>Terms of Service</h1>
        <p className="last-updated">Last updated: September 2026</p>

        <p>
          Please read these Terms of Service carefully before using FindMyProfessor.
          By accessing or using FindMyProfessor (findmyprofessor.online), you agree
          to be bound by these Terms. If you do not agree, do not use the service.
        </p>

        <h2>1. Acceptance of Terms</h2>
        <p>
          These Terms of Service ("Terms") constitute a legally binding agreement between
          you and FindMyProfessor. Your use of the platform constitutes your acceptance
          of these Terms. We reserve the right to update these Terms at any time;
          continued use of FindMyProfessor after changes are posted constitutes acceptance
          of the updated Terms.
        </p>

        <h2>2. Description of FindMyProfessor</h2>
        <p>
          FindMyProfessor is a research discovery and outreach assistance platform. It
          helps students explore potentially relevant professors and research opportunities,
          understand possible research alignment, and prepare personalized outreach emails.
          FindMyProfessor is an assistance tool — it does not guarantee any outcomes,
          placements, admissions, funding, or professor responses.
        </p>
        <p>
          FindMyProfessor is not affiliated with, endorsed by, or officially connected to
          any university, research institution, or professor listed on the platform.
        </p>

        <h2>3. User Accounts</h2>
        <p>
          You must sign in using a valid Google account through Supabase Auth to use
          FindMyProfessor. You are responsible for maintaining the security of your account.
          You must not share your account credentials or allow others to access your account.
          You must be at least 13 years old to use FindMyProfessor.
        </p>

        <h2>4. CV and User-Provided Content</h2>
        <p>
          You may upload a CV or resume to FindMyProfessor. By uploading content, you
          confirm that you have the right to do so and that the content is accurate.
          You retain ownership of your uploaded content. You grant FindMyProfessor
          permission to process, store, and use your uploaded content solely to provide
          the features of the platform (profile creation, matching, and outreach assistance).
        </p>
        <p>
          Do not upload content that belongs to someone else, contains confidential
          information you are not permitted to share, or violates any applicable law.
        </p>

        <h2>5. Professor and Research Information</h2>
        <p>
          Professor and research information displayed in FindMyProfessor is sourced from
          publicly available academic information. We do not guarantee the accuracy,
          completeness, or currency of this information. Professors listed in FindMyProfessor
          have not necessarily opted in to being contacted through the platform.
        </p>
        <p>
          You are responsible for ensuring that any outreach you send is appropriate,
          respectful, and consistent with the recipient institution's communication policies.
        </p>

        <h2>6. Personalized Email Drafts</h2>
        <p>
          FindMyProfessor may generate personalized outreach email drafts based on your
          profile and selected professor and research information. These drafts are provided
          as a starting point. You are solely responsible for reviewing, editing, and
          approving any email content before sending it.
        </p>
        <p>
          Do not send emails that are misleading, inaccurate, harassing, or that
          misrepresent your qualifications or intentions.
        </p>

        <h2>7. Gmail Integration and Email Sending</h2>
        <p>
          You may optionally connect your Gmail account to FindMyProfessor using Google's
          Gmail API (<code>gmail.send</code> scope). By connecting Gmail, you authorize
          FindMyProfessor to send email on your behalf only when you explicitly choose to
          do so.
        </p>
        <ul>
          <li>
            <strong>No automatic or bulk sending.</strong> FindMyProfessor never sends emails
            without your explicit confirmation for each individual message.
          </li>
          <li>
            <strong>You are responsible for every email sent.</strong> Connecting Gmail and
            sending an email through FindMyProfessor constitutes your personal act of
            sending that email.
          </li>
          <li>
            You may disconnect Gmail at any time from within the application, or by revoking
            access from your Google Account settings.
          </li>
        </ul>

        <h2>8. Acceptable Use</h2>
        <p>You agree not to use FindMyProfessor to:</p>
        <ul>
          <li>Send spam, unsolicited bulk messages, or harassing communications</li>
          <li>Impersonate another person or misrepresent your identity or qualifications</li>
          <li>Engage in any fraudulent, deceptive, or unlawful activity</li>
          <li>Attempt to gain unauthorized access to FindMyProfessor systems or user data</li>
          <li>Scrape, copy, or redistribute professor or research data from the platform</li>
          <li>Violate any applicable laws or regulations</li>
        </ul>
        <p>
          We reserve the right to suspend or terminate accounts that violate these Terms.
        </p>

        <h2>9. User Responsibility</h2>
        <p>
          You are solely responsible for all content you upload, all emails you choose to
          send, and all outreach activity conducted through FindMyProfessor. We are not
          responsible for any responses (or lack of response) from professors, institutions,
          or any third party.
        </p>

        <h2>10. No Guarantee of Admission, Funding, Research Position, or Professor Response</h2>
        <p>
          FindMyProfessor is a discovery and outreach assistance tool only. We make no
          guarantee, express or implied, regarding:
        </p>
        <ul>
          <li>University admission, scholarship, or funding</li>
          <li>Obtaining a research position, internship, or lab placement</li>
          <li>A professor or institution responding to your outreach</li>
          <li>The accuracy or completeness of professor or research information</li>
        </ul>
        <p>
          Results depend entirely on your qualifications, your outreach, and the independent
          decisions of professors and institutions.
        </p>

        <h2>11. Third-Party Services</h2>
        <p>
          FindMyProfessor relies on third-party services including Supabase (authentication
          and database) and Google APIs (sign-in and Gmail sending). Your use of
          these services is also subject to their respective terms and privacy policies.
          We are not responsible for the availability, accuracy, or conduct of third-party
          services.
        </p>

        <h2>12. Intellectual Property</h2>
        <p>
          The FindMyProfessor platform, including its code, design, and non-user-generated
          content, is the property of FindMyProfessor and its contributors. You may not
          copy, reproduce, or create derivative works of any part of the platform without
          permission.
        </p>
        <p>
          You retain ownership of the content you upload (CV, profile data). You grant
          FindMyProfessor a limited license to process and store that content solely to
          provide the service to you.
        </p>

        <h2>13. Service Availability</h2>
        <p>
          We aim to keep FindMyProfessor available, but we do not guarantee uninterrupted
          access. The service may be modified, suspended, or discontinued at any time.
          We are not liable for any loss or inconvenience resulting from service
          unavailability.
        </p>

        <h2>14. Limitation of Liability</h2>
        <p>
          To the maximum extent permitted by applicable law, FindMyProfessor is provided
          "as is" without warranties of any kind. We shall not be liable for any indirect,
          incidental, consequential, or special damages arising from your use of the
          platform, including but not limited to loss of data, missed opportunities,
          or any outcome related to academic or professional applications.
        </p>

        <h2>15. Changes to Terms</h2>
        <p>
          We may update these Terms from time to time. Updated Terms will be posted on
          this page with a revised "Last updated" date. Continued use of FindMyProfessor
          after changes are posted constitutes your acceptance of the revised Terms.
        </p>

        <h2>16. Contact</h2>
        <p>
          If you have questions about these Terms, please contact:
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
