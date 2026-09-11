import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Team from './Team.jsx';

function renderTeam() {
  return render(
    <MemoryRouter>
      <Team />
    </MemoryRouter>,
  );
}

describe('Team page', () => {
  it('renders the headline', () => {
    renderTeam();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /The People Behind/i,
    );
  });

  it('renders each team member with their correct name, designation, and role', () => {
    renderTeam();

    expect(screen.getByText('Safdar Mustafa')).toBeInTheDocument();
    expect(screen.getByText('Undergraduate Student, Jamia Hamdard')).toBeInTheDocument();
    expect(screen.getByText('Founder & Product Lead')).toBeInTheDocument();

    expect(screen.getByText('Dayam Nadeem')).toBeInTheDocument();
    expect(screen.getByText('Software Engineer II, InEvo AI')).toBeInTheDocument();
    expect(screen.getByText('Co-Founder')).toBeInTheDocument();

    expect(screen.getByText('Md Rehaan Alam')).toBeInTheDocument();
    expect(screen.getByText('Undergraduate Student, Galgotias University')).toBeInTheDocument();
    expect(screen.getByText('Lead Android Developer')).toBeInTheDocument();

    expect(screen.getByText('Dr. Shahab Saquib Sohail')).toBeInTheDocument();
    expect(screen.getByText('Assistant Professor, Jamia Hamdard')).toBeInTheDocument();
    expect(screen.getByText('Faculty Mentor & Academic Advisor')).toBeInTheDocument();
  });

  it('groups people into the three distinct sections', () => {
    renderTeam();
    expect(screen.getByRole('heading', { name: 'Founding Team' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Technical Contribution' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Academic Mentorship' })).toBeInTheDocument();
  });

  it('loads each photo from the correct /team/ path for the correct person', () => {
    renderTeam();

    const safdar = screen.getByAltText(/Safdar Mustafa/i);
    expect(safdar.getAttribute('src')).toBe('/team/safdar-mustafa.jpg');

    const dayam = screen.getByAltText(/Dayam Nadeem/i);
    expect(dayam.getAttribute('src')).toBe('/team/dayam-nadeem.jpg');

    const rehaan = screen.getByAltText(/Md Rehaan Alam/i);
    expect(rehaan.getAttribute('src')).toBe('/team/rehaan-alam.jpg');

    const shahab = screen.getByAltText(/Shahab Saquib Sohail/i);
    expect(shahab.getAttribute('src')).toBe('/team/shahab-saquib-sohail.jpg');
  });

  it('does not invent a founder-to-mentor reporting hierarchy label', () => {
    renderTeam();
    expect(screen.queryByText(/reports to/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Professor$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Chief Advisor|Executive Advisor|Co-Lead/i)).not.toBeInTheDocument();
  });

  it('links back to home', () => {
    renderTeam();
    const homeLinks = screen.getAllByRole('link', { name: /FindMyProfessor|Home/i });
    expect(homeLinks.some(l => l.getAttribute('href') === '/')).toBe(true);
  });
});
