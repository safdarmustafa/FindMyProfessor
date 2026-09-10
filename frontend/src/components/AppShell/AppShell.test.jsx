import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AppShell from './AppShell.jsx';
import { useGmailStatus } from '../../hooks/useGmailStatus.js';

function renderShell(path = '/matches') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell>
        <div>Page content</div>
      </AppShell>
    </MemoryRouter>,
  );
}

describe('AppShell navigation', () => {
  beforeEach(() => {
    useGmailStatus.mockReturnValue({
      status: { connected: false, email: null },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  it('renders the navbar with brand and page links', () => {
    renderShell();
    expect(screen.getByText('FindMyProfessor')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Research Matches' })).toHaveAttribute('href', '/matches');
    expect(screen.getByRole('link', { name: 'Outreach' })).toHaveAttribute('href', '/outreach/history');
    expect(screen.getByText('Page content')).toBeInTheDocument();
  });

  it('shows a green Gmail status when connected', () => {
    useGmailStatus.mockReturnValue({
      status: { connected: true, email: 'me@gmail.com' },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    renderShell();
    expect(document.querySelector('.status-dot.green')).toBeTruthy();
    expect(screen.getByText('me@gmail.com')).toBeInTheDocument();
  });

  it('shows a gray Gmail status when not connected', () => {
    renderShell();
    expect(document.querySelector('.status-dot.grey')).toBeTruthy();
    expect(document.querySelector('.status-dot.green')).toBeFalsy();
  });
});
