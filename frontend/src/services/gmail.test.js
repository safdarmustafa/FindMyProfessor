import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getGmailStatus,
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
