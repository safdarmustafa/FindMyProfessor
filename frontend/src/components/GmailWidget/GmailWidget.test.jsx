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

describe('GmailWidget when the stored connection is unusable', () => {
  it('asks the student to reconnect instead of claiming Gmail is connected', () => {
    useGmailStatus.mockReturnValue({
      status: { connected: false, email: null, needs_reconnect: true },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<GmailWidget professorId="p1" returnPath="/outreach/compose/p1" />);
    expect(screen.getByText('Your Gmail connection needs to be renewed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reconnect Gmail' })).toBeInTheDocument();
    expect(screen.queryByText(/Gmail connected/)).not.toBeInTheDocument();
  });
});
