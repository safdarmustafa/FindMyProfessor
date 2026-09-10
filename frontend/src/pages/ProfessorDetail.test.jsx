import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProfessorDetail from './ProfessorDetail.jsx';
import { professorDetail, matchingResponse, PROF_ID } from '../test/fixtures.js';
import * as matching from '../services/matching.js';

vi.mock('../services/matching.js', () => ({
  fetchMatches: vi.fn(),
  fetchProfessor: vi.fn(),
  fetchUniversities: vi.fn(),
}));

function renderDetail(id = PROF_ID) {
  return render(
    <MemoryRouter initialEntries={[`/matches/${id}`]}>
      <Routes>
        <Route path="/matches/:id" element={<ProfessorDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Professor detail page', () => {
  beforeEach(() => {
    matching.fetchProfessor.mockResolvedValue(professorDetail);
    matching.fetchMatches.mockResolvedValue(matchingResponse);
  });

  it('renders name, title, university, department, and lab', async () => {
    renderDetail();
    expect(await screen.findByRole('heading', { name: 'Jane Smith' })).toBeInTheDocument();
    expect(screen.getByText('Associate Professor')).toBeInTheDocument();
    expect(screen.getByText('Stanford University')).toBeInTheDocument();
    expect(screen.getByText('Computer Science')).toBeInTheDocument();
    expect(screen.getByText(/Vision Lab/)).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });

  it('renders research areas', async () => {
    renderDetail();
    expect((await screen.findAllByText(/Computer Vision/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Deep Learning/).length).toBeGreaterThan(0);
  });

  it('renders Why You Match', async () => {
    renderDetail();
    expect(await screen.findByText('Why You Match')).toBeInTheDocument();
    expect(screen.getByText(/Shared computer vision focus/)).toBeInTheDocument();
  });

  it('renders the opportunity section when available', async () => {
    renderDetail();
    expect(await screen.findByText(/Research Opportunit/i)).toBeInTheDocument();
    expect(screen.getByText(/PhD RA opening/)).toBeInTheDocument();
  });

  it('Prepare Personalized Email navigates to compose', async () => {
    renderDetail();
    const link = await screen.findByRole('link', { name: /Prepare Personalized Email/i });
    expect(link).toHaveAttribute('href', `/outreach/compose/${PROF_ID}`);
  });

  it('renders professor info without waiting for the slow matches re-scan', async () => {
    // fetchMatches({limit:100}) re-scores every professor just to find this
    // one's match evidence — it must never block the page's core content
    // (name/header/Prepare Email link), which only needs the fast,
    // targeted fetchProfessor call.
    matching.fetchMatches.mockReturnValue(new Promise(() => {})); // never resolves
    renderDetail();
    expect(await screen.findByRole('heading', { name: 'Jane Smith' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /Prepare Personalized Email/i })).toHaveAttribute(
      'href',
      `/outreach/compose/${PROF_ID}`,
    );
    // Match-dependent content correctly stays absent until it resolves.
    expect(screen.queryByText('Why You Match')).not.toBeInTheDocument();
  });

  it('shows an error if the professor is not found', async () => {
    matching.fetchProfessor.mockResolvedValue(null);
    matching.fetchMatches.mockResolvedValue({ matches: [] });
    renderDetail();
    expect(await screen.findByText('Professor not found')).toBeInTheDocument();
  });
});
