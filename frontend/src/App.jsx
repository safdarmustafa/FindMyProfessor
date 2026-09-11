import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Home from './pages/Home.jsx';
import Team from './pages/Team.jsx';
import Login from './pages/Login.jsx';
import Onboarding from './pages/Onboarding.jsx';
import Matches from './pages/Matches.jsx';
import ProfessorDetail from './pages/ProfessorDetail.jsx';
import EmailCompose from './pages/EmailCompose.jsx';
import OutreachHistory from './pages/OutreachHistory.jsx';
import GmailConnected from './pages/GmailConnected.jsx';
import GmailError from './pages/GmailError.jsx';
import Privacy from './pages/Privacy.jsx';
import Terms from './pages/Terms.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/team" element={<Team />} />
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/matches" element={<Matches />} />
        <Route path="/matches/:id" element={<ProfessorDetail />} />
        <Route path="/outreach/compose/:professorId" element={<EmailCompose />} />
        <Route path="/outreach/history" element={<OutreachHistory />} />
        <Route path="/outreach/gmail-connected" element={<GmailConnected />} />
        <Route path="/outreach/gmail-callback-error" element={<GmailError />} />
        <Route path="/gmail-error" element={<GmailError />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
