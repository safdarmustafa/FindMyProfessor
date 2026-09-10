import { apiFetch, apiUrl } from './api.js';

export async function getGmailStatus() {
  return apiFetch('/gmail/status');
}

export async function disconnectGmail() {
  return apiFetch('/gmail/disconnect', { method: 'POST' });
}

export function gmailConnectUrl(profileId) {
  return apiUrl('/gmail/connect?profile_id=' + encodeURIComponent(profileId));
}

const PENDING_KEY = 'fmp_pending_outreach';
const MAX_AGE_MS = 600000; // 10 minutes

export function savePendingIntent(professorId, returnPath, draftId) {
  try {
    const intent = {
      professor_id: professorId,
      return_path: returnPath,
      draft_id: draftId || null,
      timestamp: Date.now(),
    };
    localStorage.setItem(PENDING_KEY, JSON.stringify(intent));
  } catch {}
}

export function getPendingIntent() {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const intent = JSON.parse(raw);
    if (!intent || !intent.timestamp) return null;
    if (Date.now() - intent.timestamp > MAX_AGE_MS) {
      localStorage.removeItem(PENDING_KEY);
      return null;
    }
    return intent;
  } catch { return null; }
}

export function clearPendingIntent() {
  try { localStorage.removeItem(PENDING_KEY); } catch {}
}
