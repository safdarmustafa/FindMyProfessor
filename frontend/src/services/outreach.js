import { apiFetch } from './api.js';

export async function generateDraft(professorId, emailType, opportunityId) {
  const body = { professor_id: professorId, email_type: emailType };
  if (opportunityId) body.opportunity_id = opportunityId;
  return apiFetch('/outreach/drafts/generate', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getDraft(draftId) {
  return apiFetch(`/outreach/drafts/${draftId}`);
}

export async function listDrafts() {
  return apiFetch('/outreach/drafts');
}

export async function saveDraft(draftId, subject, body, status) {
  return apiFetch(`/outreach/drafts/${draftId}`, {
    method: 'PATCH',
    body: JSON.stringify({ subject, body, status }),
  });
}

export async function listCvVersions() {
  return apiFetch('/outreach/cv-versions');
}

export async function attachCv(draftId, cvVersionId) {
  return apiFetch(`/outreach/drafts/${draftId}/attach-cv`, {
    method: 'POST',
    body: JSON.stringify({ cv_version_id: cvVersionId }),
  });
}

export async function getSendPreview(draftId) {
  return apiFetch(`/outreach/drafts/${draftId}/preview`);
}

export async function sendDraft(draftId) {
  return apiFetch(`/outreach/drafts/${draftId}/send`, {
    method: 'POST',
    body: JSON.stringify({ confirmed: true }),
  });
}

export async function listHistory() {
  return apiFetch('/outreach/history');
}
