export const PROF_ID = '11111111-1111-1111-1111-111111111111';

export const professorDetail = {
  id: PROF_ID,
  name: 'Jane Smith',
  first_name: 'Jane',
  last_name: 'Smith',
  title: 'Associate Professor',
  email: 'jane@stanford.edu',
  department: { id: 'd1', name: 'Computer Science' },
  university: { id: 'u1', name: 'Stanford University' },
  lab: { id: 'l1', name: 'Vision Lab' },
  research_areas: [
    { name: 'Computer Vision' },
    { name: 'Deep Learning' },
    { name: 'Robotics' },
  ],
};

export const matchItem = {
  professor: {
    id: PROF_ID,
    name: 'Jane Smith',
    first_name: 'Jane',
    last_name: 'Smith',
    title: 'Associate Professor',
    email: 'jane@stanford.edu',
    department: { id: 'd1', name: 'Computer Science' },
    university: { id: 'u1', name: 'Stanford University' },
    lab: { id: 'l1', name: 'Vision Lab' },
    research_areas: [
      { name: 'Computer Vision' },
      { name: 'Deep Learning' },
    ],
  },
  research_match: {
    score: 87,
    priority: 'high',
    why: ['Shared computer vision focus'],
    evidence: [{ type: 'shared_research_area', area: 'Computer Vision', description: 'Shared computer vision focus' }],
  },
  research_overlap: ['Computer Vision'],
  university_opportunities: [
    { id: 'opp-1', title: 'PhD RA opening', type: 'phd', status: 'open' },
  ],
};

export const matchingResponse = {
  profile_id: 'p1',
  mode: 'research',
  match_version: '1',
  count: 1,
  matches: [matchItem],
};

export const draftResponse = {
  draft_id: 'draft-1',
  profile_id: 'p1',
  professor_id: PROF_ID,
  email_type: 'research',
  subject: 'Research inquiry from a CS student',
  body: 'Dear Professor Smith,\n\nI am writing to express interest.',
  matched_research_areas: ['Computer Vision'],
  evidence_used: [],
  generation_provider: 'test',
  generation_status: 'generated',
  professor_name: 'Jane Smith',
  professor_email: 'jane@stanford.edu',
  university_name: 'Stanford University',
};

export const historyItem = {
  draft_id: 'draft-1',
  professor_id: PROF_ID,
  professor_name: 'Jane Smith',
  university_name: 'Stanford University',
  subject: 'Research inquiry from a CS student',
  status: 'ready',
  sent_at: null,
  created_at: '2026-09-01T12:00:00Z',
};

export const cvVersions = [
  {
    cv_version_id: 'cv-1',
    display_name: 'Resume.pdf',
    file_type: 'pdf',
    is_default: true,
    confirmed: true,
  },
];
