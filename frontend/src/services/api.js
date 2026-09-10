const PROFILE_KEY = 'fmp_profile_id';

// Base URL for the FastAPI backend. Empty string keeps requests relative
// (the Vite dev proxy forwards those to localhost:8000) — set VITE_API_URL
// to call an absolute origin instead, required once frontend and backend
// are deployed as separate services.
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

export function apiUrl(path) {
  return API_BASE + path;
}

export function getProfileId() {
  try { return localStorage.getItem(PROFILE_KEY); } catch { return null; }
}

export function setProfileId(id) {
  try { localStorage.setItem(PROFILE_KEY, id); } catch {}
}

export async function apiFetch(url, options = {}) {
  const profileId = getProfileId();
  const headers = { ...options.headers };
  if (profileId) headers['X-Profile-Id'] = profileId;
  if (!(options.body instanceof FormData) && !headers['Content-Type'] && options.body) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(apiUrl(url), { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const msg = formatApiError(data.detail);
    const err = new Error(msg);
    err.status = response.status;
    throw err;
  }
  return data;
}

function formatApiError(detail) {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    const parts = detail.map((item) => {
      if (typeof item === 'string') return item;
      if (item && typeof item.msg === 'string') return item.msg;
      return null;
    }).filter(Boolean);
    if (parts.length) return parts.join(' ');
  }
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.message;
  }
  return 'Request failed.';
}
