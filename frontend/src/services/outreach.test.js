import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { generateDraft, saveDraft, sendDraft } from './outreach.js';
import { apiUrl } from './api.js';

describe('outreach service', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ draft_id: 'd1' }),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('generateDraft posts professor_id and email_type', async () => {
    await generateDraft('11111111-1111-1111-1111-111111111111', 'research', null);
    expect(fetch).toHaveBeenCalledWith(
      apiUrl('/outreach/drafts/generate'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          professor_id: '11111111-1111-1111-1111-111111111111',
          email_type: 'research',
        }),
      }),
    );
  });

  it('saveDraft patches subject, body, and status', async () => {
    await saveDraft('d1', 'Hello', 'Body text', 'ready');
    expect(fetch).toHaveBeenCalledWith(
      apiUrl('/outreach/drafts/d1'),
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ subject: 'Hello', body: 'Body text', status: 'ready' }),
      }),
    );
  });

  it('sendDraft posts confirmed: true', async () => {
    await sendDraft('d1');
    expect(fetch).toHaveBeenCalledWith(
      apiUrl('/outreach/drafts/d1/send'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ confirmed: true }),
      }),
    );
  });

  it('throws a meaningful error on 4xx', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Draft subject is empty.' }),
    });
    await expect(saveDraft('d1', '', 'x', 'ready')).rejects.toThrow('Draft subject is empty.');
  });
});
