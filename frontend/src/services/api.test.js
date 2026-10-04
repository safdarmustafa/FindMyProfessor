import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, apiUrl, getProfileId, setProfileId } from './api.js';
import { supabase } from '../lib/supabase.js';

describe('apiFetch', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('attaches X-Profile-Id when a profile is stored', async () => {
    setProfileId('p1');
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    await apiFetch('/profile');
    expect(fetch).toHaveBeenCalledWith(apiUrl('/profile'), expect.objectContaining({
      headers: expect.objectContaining({ 'X-Profile-Id': 'p1' }),
    }));
  });

  it('attaches the Supabase session token as Authorization when signed in', async () => {
    // Production hardening: the backend now verifies this token to derive
    // the authoritative profile_id instead of trusting X-Profile-Id alone
    // (app/auth.py). Without this, an authenticated user's own requests
    // would never actually exercise that verification.
    supabase.auth.getSession.mockResolvedValueOnce({
      data: { session: { access_token: 'real-jwt-token' } },
    });
    fetch.mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    await apiFetch('/profile');
    expect(fetch).toHaveBeenCalledWith(apiUrl('/profile'), expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer real-jwt-token' }),
    }));
  });

  it('omits Authorization when there is no session', async () => {
    fetch.mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    await apiFetch('/profile');
    const [, options] = fetch.mock.calls.at(-1);
    expect(options.headers.Authorization).toBeUndefined();
  });

  it('throws a string detail from FastAPI 4xx errors', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'X-Profile-Id header is required.' }),
    });
    await expect(apiFetch('/profile')).rejects.toThrow('X-Profile-Id header is required.');
  });

  it('surfaces FastAPI 422 validation arrays as a readable message', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [
          { loc: ['body', 'email_type'], msg: 'Input should be research or research_opportunity', type: 'literal_error' },
        ],
      }),
    });
    await expect(apiFetch('/outreach/drafts/generate', { method: 'POST', body: '{}' }))
      .rejects.toThrow(/research or research_opportunity/i);
  });

  it('throws a meaningful message on 5xx errors', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Database unavailable.' }),
    });
    await expect(apiFetch('/matching/professors')).rejects.toThrow('Database unavailable.');
  });
});

describe('profile id helpers', () => {
  it('round-trips profile id through localStorage', () => {
    setProfileId('abc');
    expect(getProfileId()).toBe('abc');
  });
});

describe('apiFetch keeps the stored profile id in step with the backend', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const withHeader = (value, ok = true, status = 200) => ({
    ok,
    status,
    headers: new Headers(value === undefined ? {} : { 'X-Profile-Id': value }),
    json: async () => (ok ? {} : { detail: 'No profile found for this account yet. Upload a CV first.' }),
  });

  it('replaces a stale stored id with the one the backend resolved', async () => {
    setProfileId('stale-id');
    fetch.mockResolvedValue(withHeader('real-id'));
    await apiFetch('/profile');
    expect(getProfileId()).toBe('real-id');
  });

  it('clears the stored id when the account has no profile yet, even on an error', async () => {
    setProfileId('someone-elses-id');
    fetch.mockResolvedValue(withHeader('', false, 404));
    await expect(apiFetch('/profile')).rejects.toThrow('Upload a CV first');
    expect(getProfileId()).toBeNull();
  });

  it('leaves the stored id alone when the backend sends no header', async () => {
    setProfileId('p1');
    fetch.mockResolvedValue(withHeader(undefined));
    await apiFetch('/universities');
    expect(getProfileId()).toBe('p1');
  });
});
