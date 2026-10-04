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
  listCVs: vi.fn(() => Promise.resolve([])),
  setActiveCV: vi.fn(),
  deleteCV: vi.fn(),
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
      cv_id: 'cv1',
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

describe('Onboarding review form uses the backend profile shape', () => {
  const backendProfile = {
    identity: { name: 'Ada Lovelace', email: 'ada@example.com', phone: null },
    education: [{ degree: 'B.Tech', field_of_study: 'Computer Science', institution: 'Example University', graduation_year: 2027 }],
    research_interests: ['Computer Vision', 'Medical AI'],
    research_signals: ['Edge AI'],
    skills: [{ name: 'Python', category: 'language' }],
    projects: [{ title: 'Knee OA Grading', description: 'CNN for X-rays.', technologies: ['PyTorch', 'OpenCV'] }],
    publications: [{ title: 'Efficient Imaging', venue: 'MICCAI', year: 2025, authors: 'Lovelace A.', publication_type: 'published' }],
    experience: [{ role: 'Research Intern', organization: 'Vision Lab', kind: 'research', description: 'Built models.', start_year: 2025, end_year: null }],
    certifications: [{ name: 'Deep Learning', issuer: 'Coursera', year: 2024 }],
  };

  beforeEach(() => {
    api.getProfileId.mockReturnValue('p1');
    profile.fetchProfile.mockReset();
    profile.updateProfile.mockReset();
    profile.fetchProfile.mockResolvedValue({ cv_id: 'cv1', confirmed: false, extracted_profile: backendProfile });
    profile.updateProfile.mockResolvedValue({});
  });

  it('shows parsed fields as readable values, never raw JSON', async () => {
    renderOnboarding();
    expect(await screen.findByDisplayValue('Computer Science')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Knee OA Grading')).toBeInTheDocument();
    expect(screen.getByDisplayValue('PyTorch, OpenCV')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Efficient Imaging')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Vision Lab')).toBeInTheDocument();
    expect(screen.getByDisplayValue(/Computer Vision\s+Medical AI/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/"title"\s*:/);
  });

  it('saves exactly the backend schema and keeps fields the form does not show', async () => {
    const user = userEvent.setup();
    renderOnboarding();
    await screen.findByDisplayValue('Knee OA Grading');
    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(profile.updateProfile).toHaveBeenCalled());
    const saved = profile.updateProfile.mock.calls[0][0];
    expect(saved.research_interests).toEqual(['Computer Vision', 'Medical AI']);
    expect(saved.research_signals).toEqual(['Edge AI']);
    expect(saved.education[0]).toMatchObject({ field_of_study: 'Computer Science', graduation_year: 2027 });
    expect(saved.projects[0]).toMatchObject({ title: 'Knee OA Grading', technologies: ['PyTorch', 'OpenCV'] });
    expect(saved.publications[0]).toMatchObject({ venue: 'MICCAI', year: 2025, publication_type: 'published' });
    expect(saved.experience[0]).toMatchObject({ organization: 'Vision Lab', kind: 'research', start_year: 2025 });
    expect(saved.certifications).toEqual(backendProfile.certifications);
    expect(saved.skills).toEqual([{ name: 'Python', category: 'language' }]);
    expect(saved).not.toHaveProperty('research');
  });
});

describe('My CV library', () => {
  const versions = [
    { cv_id: 'new', file_name: 'CV_2026.pdf', file_type: 'pdf', file_size: 300000, created_at: '2026-10-04T10:00:00Z', is_default: true, confirmed: true, file_available: true },
    { cv_id: 'old', file_name: 'Old_CV.pdf', file_type: 'pdf', file_size: 600000, created_at: '2026-09-12T10:00:00Z', is_default: false, confirmed: false, file_available: false },
  ];

  beforeEach(() => {
    api.getProfileId.mockReturnValue('p1');
    profile.fetchProfile.mockReset();
    profile.listCVs.mockReset();
    profile.deleteCV.mockReset();
    profile.setActiveCV.mockReset();
    profile.fetchProfile.mockResolvedValue({ cv_id: 'new', confirmed: true, extracted_profile: { research_interests: ['Medical AI'] } });
    profile.listCVs.mockResolvedValue(versions);
  });

  it('lists every CV with its state', async () => {
    renderOnboarding();
    const rows = await screen.findAllByTestId('cv-row');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('CV_2026.pdf');
    expect(rows[0]).toHaveTextContent('Active');
    expect(rows[0]).toHaveTextContent('Confirmed');
    expect(rows[1]).toHaveTextContent('File missing');
  });

  it('deletes a CV only after an inline confirmation', async () => {
    const user = userEvent.setup();
    profile.deleteCV.mockResolvedValue([versions[0]]);
    renderOnboarding();
    await screen.findAllByTestId('cv-row');

    await user.click(screen.getByRole('button', { name: 'Delete Old_CV.pdf' }));
    expect(profile.deleteCV).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: /^Delete$/ }));

    await waitFor(() => expect(profile.deleteCV).toHaveBeenCalledWith('old'));
    await waitFor(() => expect(screen.getAllByTestId('cv-row')).toHaveLength(1));
  });

  it('switches the active CV and reloads that CV\'s profile', async () => {
    const user = userEvent.setup();
    const both = [
      { ...versions[0] },
      { ...versions[1], file_available: true, confirmed: true },
    ];
    profile.listCVs.mockResolvedValue(both);
    profile.setActiveCV.mockResolvedValue([
      { ...both[0], is_default: false },
      { ...both[1], is_default: true },
    ]);
    renderOnboarding();
    await screen.findAllByTestId('cv-row');

    await user.click(screen.getByRole('button', { name: 'Make active' }));
    await waitFor(() => expect(profile.setActiveCV).toHaveBeenCalledWith('old'));
    expect(profile.fetchProfile).toHaveBeenCalledTimes(2);
  });

  it('offers an upload of a new CV from the confirmed screen', async () => {
    const user = userEvent.setup();
    renderOnboarding();
    await user.click(await screen.findByRole('button', { name: 'Upload a new CV' }));
    expect(document.getElementById('cv-upload-input')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Keep my current CV/ })).toBeInTheDocument();
  });
});

describe('My CV library cleanup', () => {
  it('removes every CV with a missing file after one confirmation', async () => {
    const user = userEvent.setup();
    const active = { cv_id: 'new', file_name: 'CV.pdf', is_default: true, confirmed: true, file_available: true };
    const dead = ['a', 'b', 'c'].map(id => ({ cv_id: id, file_name: `${id}.pdf`, is_default: false, confirmed: false, file_available: false }));
    api.getProfileId.mockReturnValue('p1');
    profile.fetchProfile.mockReset();
    profile.fetchProfile.mockResolvedValue({ cv_id: 'new', confirmed: true, extracted_profile: {} });
    profile.listCVs.mockReset();
    profile.listCVs.mockResolvedValue([active, ...dead]);
    profile.deleteCV.mockReset();
    profile.deleteCV
      .mockResolvedValueOnce([active, dead[1], dead[2]])
      .mockResolvedValueOnce([active, dead[2]])
      .mockResolvedValueOnce([active]);

    renderOnboarding();
    await user.click(await screen.findByRole('button', { name: 'Remove missing CVs' }));
    await user.click(screen.getByRole('button', { name: 'Remove all' }));

    await waitFor(() => expect(profile.deleteCV).toHaveBeenCalledTimes(3));
    expect(profile.deleteCV.mock.calls.map(c => c[0])).toEqual(['a', 'b', 'c']);
    await waitFor(() => expect(screen.getAllByTestId('cv-row')).toHaveLength(1));
  });
});
