import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getGmailStatus,
  gmailConnectUrl,
  savePendingIntent,
  getPendingIntent,
  clearPendingIntent,
} from './gmail.js';
import { apiUrl } from './api.js';

describe('gmail service', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('getStatus returns the connected state', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ connected: true, email: 'me@gmail.com' }),
    });
    await expect(getGmailStatus()).resolves.toEqual({ connected: true, email: 'me@gmail.com' });
    expect(fetch).toHaveBeenCalledWith(apiUrl('/gmail/status'), expect.any(Object));
  });

  it('throws a meaningful error on 4xx/5xx', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'X-Profile-Id header is required.' }),
    });
    await expect(getGmailStatus()).rejects.toThrow('X-Profile-Id header is required.');
  });

  it('gmailConnectUrl includes return_to when provided', () => {
    const url = gmailConnectUrl('p1', '/outreach/compose/prof-9');
    expect(url).toBe(apiUrl('/gmail/connect?profile_id=p1&return_to=%2Foutreach%2Fcompose%2Fprof-9'));
  });

  it('gmailConnectUrl omits return_to when not provided', () => {
    const url = gmailConnectUrl('p1');
    expect(url).toBe(apiUrl('/gmail/connect?profile_id=p1'));
  });

  it('pending intent is stored, read, and cleared', () => {
    savePendingIntent('p1', '/outreach/compose/p1');
    expect(getPendingIntent()).toMatchObject({
      professor_id: 'p1',
      return_path: '/outreach/compose/p1',
    });
    clearPendingIntent();
    expect(getPendingIntent()).toBeNull();
  });
});
