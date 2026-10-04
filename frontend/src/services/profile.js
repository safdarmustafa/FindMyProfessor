import { apiFetch } from './api.js';

export async function fetchProfile() {
  return apiFetch('/profile');
}

export async function updateProfile(extractedProfile) {
  return apiFetch('/profile', {
    method: 'PUT',
    body: JSON.stringify({ extracted_profile: extractedProfile }),
  });
}

export async function confirmProfile() {
  return apiFetch('/profile/confirm', { method: 'POST' });
}

export async function uploadCV(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch('/cv/upload', {
    method: 'POST',
    body: formData,
  });
}

// ── CV library (My CV page) ─────────────────────────────
export async function listCVs() {
  return apiFetch('/cv');
}

export async function setActiveCV(cvId) {
  return apiFetch(`/cv/${encodeURIComponent(cvId)}/default`, { method: 'POST' });
}

export async function deleteCV(cvId) {
  return apiFetch(`/cv/${encodeURIComponent(cvId)}`, { method: 'DELETE' });
}
