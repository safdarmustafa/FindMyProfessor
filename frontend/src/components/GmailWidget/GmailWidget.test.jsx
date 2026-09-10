import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GmailWidget from './GmailWidget.jsx';
import { useGmailStatus } from '../../hooks/useGmailStatus.js';
import * as gmail from '../../services/gmail.js';

vi.mock('../../services/gmail.js', async () => {
  const actual = await vi.importActual('../../services/gmail.js');
  return { ...actual, disconnectGmail: vi.fn() };
});

describe('GmailWidget', () => {
  beforeEach(() => {
    useGmailStatus.mockReturnValue({
      status: { connected: true, email: 'me@gmail.com' },
      loading: false,
      error: null,
      refetch: vi.fn().mockResolvedValue(undefined),
    });
  });

  it('shows a clear error instead of silently failing when disconnect fails', async () => {
    // Previously a failed disconnectGmail() was swallowed entirely — the
    // button just reset with no feedback, leaving the user unsure whether
    // Gmail was actually disconnected.
    gmail.disconnectGmail.mockRejectedValue(new Error('Network error.'));
    const user = userEvent.setup();
    render(<GmailWidget />);

    await user.click(screen.getByRole('button', { name: /Disconnect/i }));

    expect(await screen.findByText('Network error.')).toBeInTheDocument();
    // Still shows as connected — the disconnect did not actually happen.
    expect(screen.getByText('me@gmail.com')).toBeInTheDocument();
  });

  it('disconnects cleanly with no error banner on success', async () => {
    gmail.disconnectGmail.mockResolvedValue({ disconnected: true });
    const user = userEvent.setup();
    render(<GmailWidget />);

    await user.click(screen.getByRole('button', { name: /Disconnect/i }));

    expect(gmail.disconnectGmail).toHaveBeenCalled();
    expect(screen.queryByText('Network error.')).not.toBeInTheDocument();
  });
});
