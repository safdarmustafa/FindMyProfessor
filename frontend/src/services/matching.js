import { apiFetch } from './api.js';

export async function fetchMatches(opts = {}) {
  const params = new URLSearchParams();
  params.set('mode', opts.mode || 'research');
  if (opts.limit) params.set('limit', opts.limit);
  if (opts.university_id) params.set('university_id', opts.university_id);
  if (opts.min_score != null && opts.min_score !== '') params.set('min_score', opts.min_score);
  if (opts.email_only) params.set('email_only', 'true');
  if (opts.opportunity_type) params.set('opportunity_type', opts.opportunity_type);
  if (opts.opportunity_status) params.set('opportunity_status', opts.opportunity_status);
  return apiFetch(`/matching/professors?${params.toString()}`);
}

export async function fetchUniversities() {
  return apiFetch('/universities');
}

export async function fetchProfessor(professorId) {
  return apiFetch(`/professors/${professorId}`);
}
