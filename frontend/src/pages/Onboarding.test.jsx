import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Onboarding from './Onboarding.jsx';
import * as profile from '../services/profile.js';
import * as api from '../services/api.js';

vi.mock('../services/profile.js', () => ({
  uploadCV: vi.fn(),
  fetchProfile: vi.fn(),
  updateProfile: vi.fn(),
  confirmProfile: vi.fn(),
}));

vi.mock('../services/api.js', async () => {
  const actual = await vi.importActual('../services/api.js');
  return {
    ...actual,
    getProfileId: vi.fn(() => null),
    setProfileId: vi.fn(),
  };
});

function renderOnboarding() {
  return render(
    <MemoryRouter>
      <Onboarding />
    </MemoryRouter>,
  );
}

describe('Onboarding page', () => {
  beforeEach(() => {
    api.getProfileId.mockReturnValue(null);
    profile.uploadCV.mockReset();
    profile.fetchProfile.mockReset();
  });

  it('renders the CV upload area', () => {
    renderOnboarding();
    expect(screen.getByText(/Build Your Research Profile/i)).toBeInTheDocument();
    expect(document.getElementById('cv-upload-input')).toBeTruthy();
  });

  it('uploading a PDF calls the CV upload API', async () => {
    const user = userEvent.setup();
    profile.uploadCV.mockResolvedValue({
      profile_id: 'p1',
      extracted_profile: {
        identity: { name: 'Ada' },
        research: { interests: ['Computer Vision'] },
        skills: [],
        education: [],
        projects: [],
      },
    });

    renderOnboarding();
    const input = document.getElementById('cv-upload-input');
    const file = new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' });
    await user.upload(input, file);
    await user.click(screen.getByRole('button', { name: /Analyze CV/i }));

    await waitFor(() => {
      expect(profile.uploadCV).toHaveBeenCalledWith(file);
    });
  });

  it('shows extracted research interests after upload', async () => {
    const user = userEvent.setup();
    profile.uploadCV.mockResolvedValue({
      profile_id: 'p1',
      extracted_profile: {
        identity: { name: 'Ada Lovelace' },
        research: { interests: ['Computer Vision', 'NLP'] },
        skills: [],
        education: [],
        projects: [],
      },
    });

    renderOnboarding();
    const input = document.getElementById('cv-upload-input');
    await user.upload(input, new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: /Analyze CV/i }));

    expect(await screen.findByDisplayValue(/Computer Vision/)).toBeInTheDocument();
    expect(screen.getByText(/Review your research profile/i)).toBeInTheDocument();
  });

  it('Find Matching Professors navigates to /matches after confirm', async () => {
    api.getProfileId.mockReturnValue('p1');
    profile.fetchProfile.mockResolvedValue({
      confirmed: true,
      extracted_profile: { research: { interests: ['CV'] } },
    });

    renderOnboarding();
    const link = await screen.findByRole('link', { name: /Find Matching Professors/i });
    expect(link).toHaveAttribute('href', '/matches');
  });

  it('shows an error if upload fails', async () => {
    const user = userEvent.setup();
    profile.uploadCV.mockRejectedValue(new Error('File too large.'));

    renderOnboarding();
    const input = document.getElementById('cv-upload-input');
    await user.upload(input, new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: /Analyze CV/i }));

    expect(await screen.findByText('File too large.')).toBeInTheDocument();
  });
});
