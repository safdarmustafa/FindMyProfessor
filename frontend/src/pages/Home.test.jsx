import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Home from './Home.jsx';

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  );
}

describe('Home page', () => {
  it('renders the headline', () => {
    renderHome();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /Find the professors behind/i,
    );
    expect(screen.getByText(/the research you want to pursue/i)).toBeInTheDocument();
  });

  it('Get Started buttons navigate to /login', () => {
    renderHome();
    const links = screen.getAllByRole('link', { name: /Get Started/i });
    expect(links.length).toBeGreaterThan(0);
    links.forEach(link => {
      expect(link).toHaveAttribute('href', '/login');
    });
  });

  it('See How It Works scrolls to the how-it-works section', () => {
    renderHome();
    const link = screen.getByRole('link', { name: /See How It Works/i });
    expect(link).toHaveAttribute('href', '#how-it-works');
    expect(document.getElementById('how-it-works')).toBeTruthy();
  });

  it('shows the 5-step academic discovery flow', () => {
    renderHome();
    expect(screen.getByText('CV Upload')).toBeInTheDocument();
    expect(screen.getByText('Research Profile')).toBeInTheDocument();
    expect(screen.getByText('Professor Discovery')).toBeInTheDocument();
    expect(screen.getByText('Research Match')).toBeInTheDocument();
    expect(screen.getByText('Personalized Outreach')).toBeInTheDocument();
  });
});
