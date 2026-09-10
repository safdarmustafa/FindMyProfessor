import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GmailError from './GmailError.jsx';
import * as api from '../services/api.js';

vi.mock('../services/api.js', async () => {
  const actual = await vi.importActual('../services/api.js');
  return { ...actual, getProfileId: vi.fn(() => 'p1') };
});

function renderError(search = '?reason=denied') {
  return render(
    <MemoryRouter initialEntries={[`/outreach/gmail-callback-error${search}`]}>
      <GmailError />
    </MemoryRouter>,
  );
}

describe('Gmail error page', () => {
  it('renders the error heading', () => {
    renderError();
    expect(screen.getByRole('heading', { name: /Gmail Connection Failed/i })).toBeInTheDocument();
  });

  it('shows the reason from the URL param', () => {
    renderError('?reason=denied');
    expect(screen.getByText(/denied/i)).toBeInTheDocument();
  });

  it('shows a Try Again button when a profile exists', () => {
    api.getProfileId.mockReturnValue('p1');
    renderError();
    expect(screen.getByRole('link', { name: /Try Again/i })).toBeInTheDocument();
  });
});
