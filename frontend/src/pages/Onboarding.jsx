import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AppShell from '../components/AppShell/AppShell.jsx';
import Spinner from '../components/Spinner.jsx';
import CvLibrary from '../components/CvLibrary/CvLibrary.jsx';
import {
  uploadCV, fetchProfile, updateProfile, confirmProfile, listCVs, setActiveCV, deleteCV,
} from '../services/profile.js';
import { getProfileId, setProfileId } from '../services/api.js';

const STEPS = ['Upload CV', 'Review Profile', 'Confirm'];

/* ── Step indicator ───────────────────────────────────── */
function StepIndicator({ step }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginBottom: '2.25rem' }}>
      {STEPS.map((label, i) => {
        const n = i + 1;
        const active = step === n;
        const done = step > n;
        return (
          <React.Fragment key={i}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '.3rem' }}>
              <div style={{
                width: '28px', height: '28px', borderRadius: '50%',
                background: done ? 'var(--green)' : active ? 'var(--navy)' : 'var(--line)',
                color: done || active ? '#fff' : 'var(--muted)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '.75rem', fontWeight: 700, flexShrink: 0,
                transition: 'background .2s',
              }}>
                {done ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <path d="M20 6L9 17l-5-5"/>
                  </svg>
                ) : n}
              </div>
              <span style={{
                fontSize: '.72rem',
                fontWeight: active ? 700 : 500,
                color: active ? 'var(--navy)' : done ? 'var(--green)' : 'var(--muted)',
                whiteSpace: 'nowrap',
              }}>
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{
                flex: 1,
                height: '2px',
                background: done ? 'var(--green)' : 'var(--line)',
                marginBottom: '1.2rem',
                transition: 'background .2s',
              }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ── Helpers ──────────────────────────────────────────── */
// The form edits exactly the backend's ExtractedStudentProfile shape
// (app/cv/extraction/schema.py). Anything the form doesn't show — e.g.
// certifications, experience years — is carried over from the parsed profile
// unchanged, so saving never silently drops data.
const SKILL_CATEGORIES = ['language', 'framework', 'ml_tool', 'database', 'cloud', 'other'];

function parseList(text) {
  if (!text) return [];
  return text.split('\n').map(s => s.trim()).filter(Boolean);
}

function parseSkills(text) {
  return parseList(text).map(line => {
    const [name, category] = line.split('|').map(p => p.trim());
    const cat = (category || '').toLowerCase().replace(/[\s-]+/g, '_');
    return { name, category: SKILL_CATEGORIES.includes(cat) ? cat : 'other' };
  }).filter(s => s.name);
}

function parseTags(text) {
  return (text || '').split(',').map(t => t.trim()).filter(Boolean);
}

function toYear(value) {
  const n = parseInt(String(value || '').trim(), 10);
  return Number.isFinite(n) && n > 1900 && n < 2100 ? n : null;
}

function clean(value) {
  const v = typeof value === 'string' ? value.trim() : value;
  return v === '' || v === undefined ? null : v;
}

/* ── Editable list of cards (projects, publications, experience) ── */
function ItemListEditor({ title, items, fields, onChange, addLabel, emptyItem }) {
  const update = (index, key, value) =>
    onChange(items.map((item, i) => (i === index ? { ...item, [key]: value } : item)));
  const remove = (index) => onChange(items.filter((_, i) => i !== index));
  const add = () => onChange([...items, { ...emptyItem }]);

  return (
    <fieldset style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-md)', padding: '1.1rem' }}>
      <legend style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '.8125rem', padding: '0 .4rem' }}>{title}</legend>
      {items.length === 0 && (
        <p style={{ color: 'var(--muted)', fontSize: '.8125rem', margin: '0 0 .75rem' }}>Nothing found on your CV. Add one below if needed.</p>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '.9rem' }}>
        {items.map((item, index) => (
          <div key={index} style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-md)', padding: '.85rem', background: 'var(--bg)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.6rem' }}>
              {fields.map(({ key, label, type, options, span }) => (
                <div key={key} className="form-group" style={{ gridColumn: span === 'full' ? '1 / -1' : 'auto', margin: 0 }}>
                  <label className="form-label">{label}</label>
                  {type === 'textarea' ? (
                    <textarea className="form-textarea" rows={3} value={item[key] ?? ''} onChange={e => update(index, key, e.target.value)} />
                  ) : type === 'select' ? (
                    <select className="form-input" value={item[key] ?? ''} onChange={e => update(index, key, e.target.value)}>
                      {options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                    </select>
                  ) : (
                    <input className="form-input" value={item[key] ?? ''} onChange={e => update(index, key, e.target.value)} />
                  )}
                </div>
              ))}
            </div>
            <button type="button" onClick={() => remove(index)} style={{
              marginTop: '.6rem', background: 'none', border: 'none', color: 'var(--red, #b42318)',
              fontSize: '.78rem', cursor: 'pointer', padding: 0,
            }}>
              Remove
            </button>
          </div>
        ))}
      </div>
      <button type="button" onClick={add} style={{
        marginTop: '.85rem', padding: '.45rem .9rem', background: 'var(--card)', color: 'var(--navy)',
        border: '1px dashed var(--line)', borderRadius: 'var(--r-md)', fontSize: '.8125rem', cursor: 'pointer',
      }}>
        + {addLabel}
      </button>
    </fieldset>
  );
}

const PROJECT_FIELDS = [
  { key: 'title', label: 'Title', span: 'full' },
  { key: 'description', label: 'What you did', type: 'textarea', span: 'full' },
  { key: 'technologies', label: 'Technologies (comma separated)', span: 'full' },
];
const PUBLICATION_FIELDS = [
  { key: 'title', label: 'Title', span: 'full' },
  { key: 'venue', label: 'Venue (conference / journal)', span: 'full' },
  { key: 'year', label: 'Year' },
  { key: 'publication_type', label: 'Status', type: 'select', options: [
    ['', '—'], ['published', 'Published'], ['accepted', 'Accepted'], ['under review', 'Under review'], ['preprint', 'Preprint'],
  ] },
  { key: 'authors', label: 'Authors', span: 'full' },
];
const EXPERIENCE_FIELDS = [
  { key: 'role', label: 'Role' },
  { key: 'organization', label: 'Organization' },
  { key: 'kind', label: 'Type', type: 'select', options: [
    ['', '—'], ['research', 'Research'], ['internship', 'Internship'], ['work', 'Work'], ['other', 'Other'],
  ] },
  { key: 'years', label: 'Years (e.g. 2025 – 2026)' },
  { key: 'description', label: 'Description', type: 'textarea', span: 'full' },
];

function projectToForm(p) {
  return { ...p, title: p.title || '', description: p.description || '', technologies: (p.technologies || []).join(', ') };
}
function publicationToForm(p) {
  return { ...p, title: p.title || '', venue: p.venue || '', year: p.year ?? '', authors: p.authors || '', publication_type: p.publication_type || '' };
}
function experienceToForm(e) {
  const years = [e.start_year, e.end_year].filter(Boolean).join(' – ');
  return { ...e, role: e.role || '', organization: e.organization || '', kind: e.kind || '', description: e.description || '', years };
}
function projectFromForm(p) {
  return { title: (p.title || '').trim(), description: clean(p.description), technologies: parseTags(p.technologies), research_relevance: clean(p.research_relevance) };
}
function publicationFromForm(p) {
  return { title: (p.title || '').trim(), venue: clean(p.venue), year: toYear(p.year), authors: clean(p.authors), publication_type: clean(p.publication_type) };
}
function experienceFromForm(e) {
  const years = String(e.years || '').match(/(19|20)\d{2}/g) || [];
  return {
    role: clean(e.role), organization: clean(e.organization),
    kind: ['internship', 'research', 'work', 'other'].includes(e.kind) ? e.kind : null,
    description: clean(e.description),
    start_year: years[0] ? Number(years[0]) : null,
    end_year: years[1] ? Number(years[1]) : null,
  };
}

/* ── Main component ───────────────────────────────────── */
export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Step 1
  const fileInputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Step 2 (form fields)
  const [formData, setFormData] = useState({
    name: '', email: '', phone: '',
    degree: '', field: '', institution: '', country: '', grad_year: '', semester: '',
    research_interests: '', signals: '', skills: '',
    projects: [], publications: [], experience: [],
  });
  // The parsed profile as the backend returned it; fields the form doesn't
  // edit are carried over from here on save.
  const [original, setOriginal] = useState({});
  const [saving, setSaving] = useState(false);

  // Step 3
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  // CV library
  const [versions, setVersions] = useState([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [cvBusyId, setCvBusyId] = useState(null);
  const [cvError, setCvError] = useState(null);
  const stepCardRef = useRef(null);

  // Show the active CV's profile at the right step. With no CV at all the
  // backend still returns an empty profile, so key off cv_id, not the profile.
  function applyProfile(data) {
    setProfile(data && data.cv_id ? data : null);
    setConfirmed(Boolean(data?.cv_id && data.confirmed));
    if (!data || !data.cv_id) {
      setStep(1);
      return;
    }
    if (data.extracted_profile) populateForm(data.extracted_profile);
    setStep(data.confirmed ? 3 : 2);
  }

  async function refreshVersions() {
    setVersionsLoading(true);
    try {
      setVersions(await listCVs());
    } catch {
      setVersions([]);
    } finally {
      setVersionsLoading(false);
    }
  }

  async function refreshAll() {
    const [data] = await Promise.all([fetchProfile().catch(() => null), refreshVersions()]);
    applyProfile(data);
  }

  useEffect(() => {
    if (!getProfileId()) return;
    setLoading(true);
    refreshAll().finally(() => setLoading(false));
  }, []);

  function startNewUpload() {
    setSelectedFile(null);
    setError(null);
    setStep(1);
    stepCardRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }

  async function handleMakeActive(cvId) {
    setCvBusyId(cvId);
    setCvError(null);
    try {
      setVersions(await setActiveCV(cvId));
      applyProfile(await fetchProfile());
    } catch (e) {
      setCvError(e.message || 'Could not switch the active CV. Please try again.');
    } finally {
      setCvBusyId(null);
    }
  }

  async function handleRemoveMissing(cvIds) {
    setCvBusyId('bulk');
    setCvError(null);
    try {
      let latest = versions;
      for (const id of cvIds) latest = await deleteCV(id);
      setVersions(latest);
      applyProfile(await fetchProfile().catch(() => null));
    } catch (e) {
      setCvError(e.message || 'Could not remove every missing CV. Please try again.');
      refreshVersions();
    } finally {
      setCvBusyId(null);
    }
  }

  async function handleDeleteCv(cvId) {
    setCvBusyId(cvId);
    setCvError(null);
    try {
      setVersions(await deleteCV(cvId));
      applyProfile(await fetchProfile().catch(() => null));
    } catch (e) {
      setCvError(e.message || 'Could not delete this CV. Please try again.');
    } finally {
      setCvBusyId(null);
    }
  }

  function populateForm(ep) {
    const identity = ep.identity || {};
    const education = (ep.education || [])[0] || {};
    // Older payloads nested interests under `research`; accept both.
    const interests = ep.research_interests || ep.research?.interests || [];
    const signals = ep.research_signals || ep.research?.signals || [];
    setOriginal(ep);
    setFormData({
      name: identity.name || '',
      email: identity.email || '',
      phone: identity.phone || '',
      degree: education.degree || '',
      field: education.field_of_study || education.field || '',
      institution: education.institution || '',
      country: education.country || '',
      grad_year: education.graduation_year ?? education.grad_year ?? '',
      semester: education.current_semester || education.semester || '',
      research_interests: interests.join('\n'),
      signals: signals.join('\n'),
      skills: (ep.skills || []).map(s => typeof s === 'string' ? s : `${s.name} | ${s.category || 'other'}`).join('\n'),
      projects: (Array.isArray(ep.projects) ? ep.projects : []).map(projectToForm),
      publications: (Array.isArray(ep.publications) ? ep.publications : []).map(publicationToForm),
      experience: (Array.isArray(ep.experience) ? ep.experience : []).map(experienceToForm),
    });
  }

  function collectProfile() {
    const firstEducation = (original.education || [])[0] || {};
    const hasEducation = [formData.degree, formData.field, formData.institution, formData.country, formData.grad_year, formData.semester]
      .some(v => String(v ?? '').trim());
    return {
      ...original,
      identity: { name: clean(formData.name), email: clean(formData.email), phone: clean(formData.phone) },
      education: [
        ...(hasEducation ? [{
          ...firstEducation,
          degree: clean(formData.degree),
          field_of_study: clean(formData.field),
          institution: clean(formData.institution),
          country: clean(formData.country),
          graduation_year: toYear(formData.grad_year),
          current_semester: clean(String(formData.semester ?? '')),
        }] : []),
        ...(original.education || []).slice(1),
      ],
      research_interests: parseList(formData.research_interests),
      research_signals: parseList(formData.signals),
      skills: parseSkills(formData.skills),
      projects: formData.projects.map(projectFromForm).filter(p => p.title),
      publications: formData.publications.map(publicationFromForm).filter(p => p.title),
      experience: formData.experience.map(experienceFromForm).filter(e => e.role || e.organization || e.description),
      certifications: original.certifications || [],
    };
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  }, []);

  const handleDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const handleDragLeave = () => setDragging(false);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    try {
      const data = await uploadCV(selectedFile);
      if (data.profile_id) setProfileId(data.profile_id);
      setProfile(data);
      setConfirmed(false);
      setSelectedFile(null);
      if (data.extracted_profile) populateForm(data.extracted_profile);
      setStep(2);
      refreshVersions();
    } catch (e) {
      setError(e.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const ep = collectProfile();
      await updateProfile(ep);
      setConfirmed(false);
      setStep(3);
      refreshVersions();
    } catch (e) {
      setError(e.message || 'Save failed. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    setError(null);
    try {
      await confirmProfile();
      setConfirmed(true);
      refreshVersions();
    } catch (e) {
      setError(e.message || 'Confirmation failed. Please try again.');
    } finally {
      setConfirming(false);
    }
  };

  const ff = (k) => (e) => setFormData(d => ({ ...d, [k]: e.target.value }));
  const ACCEPTED = '.pdf,.doc,.docx,.txt,.rtf,.odt';

  return (
    <AppShell>
      <div style={{ minHeight: 'calc(100vh - var(--nav-h))', background: 'var(--bg)', padding: '2.5rem 1.5rem' }}>
        <div style={{ maxWidth: '680px', margin: '0 auto' }}>

          {/* Page header */}
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h1 style={{
              fontFamily: 'var(--font-serif)',
              fontSize: 'clamp(1.3rem, 3vw, 1.65rem)',
              color: 'var(--navy)',
              marginBottom: '.4rem',
            }}>
              Build Your Research Profile
            </h1>
            <p style={{ color: 'var(--muted)', fontSize: '.875rem' }}>
              Upload your CV to get started with professor matching.
            </p>
          </div>

          {(versions.length > 0 || versionsLoading) && (
            <CvLibrary
              versions={versions}
              loading={versionsLoading}
              busyId={cvBusyId}
              error={cvError}
              onUploadNew={startNewUpload}
              onMakeActive={handleMakeActive}
              onDelete={handleDeleteCv}
              onRemoveMissing={handleRemoveMissing}
            />
          )}

          {/* White card wrapper */}
          <div ref={stepCardRef} style={{
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: 'var(--r-xl)',
            padding: '2rem',
            boxShadow: 'var(--shadow-sm)',
          }}>
            <StepIndicator step={step} />

            {loading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', padding: '1.5rem', justifyContent: 'center', color: 'var(--muted)', fontSize: '.875rem' }}>
                <Spinner size={16} /> Loading your profile…
              </div>
            )}

            {error && (
              <div className="banner banner-error" style={{ marginBottom: '1.25rem' }}>
                {error}
              </div>
            )}

            {/* ── Step 1: Upload ────────────────────────── */}
            {step === 1 && !loading && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED}
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                  id="cv-upload-input"
                />

                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    border: `2px dashed ${dragging ? 'var(--navy)' : selectedFile ? 'var(--green)' : 'var(--line)'}`,
                    borderRadius: 'var(--r-lg)',
                    padding: '3rem 1.5rem',
                    textAlign: 'center',
                    cursor: 'pointer',
                    background: dragging ? 'var(--accent-bg)' : selectedFile ? 'var(--green-bg)' : 'var(--bg)',
                    transition: 'all .15s',
                  }}
                >
                  {selectedFile ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '.6rem' }}>
                      <div style={{
                        width: '52px', height: '52px',
                        background: 'var(--green-bg)',
                        border: '1px solid var(--green-bdr)',
                        borderRadius: 'var(--r-md)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: 'var(--green)',
                      }}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                          <polyline points="14 2 14 8 20 8"/>
                        </svg>
                      </div>
                      <div style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '.9375rem' }}>{selectedFile.name}</div>
                      <div style={{ fontSize: '.8rem', color: 'var(--muted)' }}>
                        {(selectedFile.size / 1024).toFixed(1)} KB · {selectedFile.type || 'document'}
                      </div>
                      <div style={{ fontSize: '.8rem', color: 'var(--green)', fontWeight: 600 }}>✓ Ready to analyze</div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '.75rem' }}>
                      <div style={{
                        width: '56px', height: '56px',
                        background: 'var(--line-light)',
                        borderRadius: 'var(--r-md)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: 'var(--subtle)',
                      }}>
                        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                          <polyline points="17 8 12 3 7 8"/>
                          <line x1="12" y1="3" x2="12" y2="15"/>
                        </svg>
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, color: 'var(--ink)', fontSize: '1rem', marginBottom: '.25rem' }}>
                          Drop your CV here or click to browse
                        </div>
                        <div style={{ fontSize: '.8125rem', color: 'var(--muted)' }}>
                          PDF, Word (.doc/.docx), RTF, ODT, or plain text
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {selectedFile && (
                  <button
                    onClick={handleUpload}
                    disabled={uploading}
                    style={{
                      width: '100%',
                      marginTop: '1.25rem',
                      padding: '.8rem',
                      background: 'var(--navy)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 'var(--r-md)',
                      fontSize: '.9375rem',
                      fontWeight: 700,
                      cursor: uploading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '.5rem',
                      opacity: uploading ? .7 : 1,
                    }}
                  >
                    {uploading ? <><Spinner size={16} color="#fff" /> Analyzing CV…</> : 'Analyze CV'}
                  </button>
                )}

                {profile && profile.extracted_profile && (
                  <button
                    onClick={() => { setSelectedFile(null); setStep(confirmed ? 3 : 2); }}
                    style={{
                      width: '100%',
                      marginTop: '.65rem',
                      padding: '.7rem',
                      background: 'transparent',
                      color: 'var(--muted)',
                      border: '1px solid var(--line)',
                      borderRadius: 'var(--r-md)',
                      fontSize: '.875rem',
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    Keep my current CV →
                  </button>
                )}
              </>
            )}

            {/* ── Step 2: Review ────────────────────────── */}
            {step === 2 && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                  <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--navy)', margin: 0 }}>Review your research profile</h2>
                  {profile?.parsing_status && (
                    <span className={`badge ${profile.parsing_status === 'success' ? 'badge-green' : 'badge-amber'}`}>
                      {profile.parsing_status}
                    </span>
                  )}
                </div>

                {profile?.parsing_error && (
                  <div className="banner banner-warning" style={{ marginBottom: '1rem' }}>
                    Parsing note: {profile.parsing_error}
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  {/* Identity */}
                  <fieldset style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-md)', padding: '1.1rem' }}>
                    <legend style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '.8125rem', padding: '0 .4rem' }}>Identity</legend>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.75rem' }}>
                      {[['name','Full name'],['email','Email'],['phone','Phone']].map(([k, lbl]) => (
                        <div key={k} className="form-group" style={{ gridColumn: k === 'name' ? '1 / -1' : 'auto' }}>
                          <label className="form-label">{lbl}</label>
                          <input className="form-input" value={formData[k]} onChange={ff(k)} placeholder={lbl} />
                        </div>
                      ))}
                    </div>
                  </fieldset>

                  {/* Education */}
                  <fieldset style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-md)', padding: '1.1rem' }}>
                    <legend style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '.8125rem', padding: '0 .4rem' }}>Education</legend>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.75rem' }}>
                      {[
                        ['degree','Degree','auto'], ['field','Field of study','auto'],
                        ['institution','Institution','1 / -1'], ['country','Country','auto'],
                        ['grad_year','Grad year','auto'], ['semester','Semester/term','auto'],
                      ].map(([k, lbl, gc]) => (
                        <div key={k} className="form-group" style={{ gridColumn: gc || 'auto' }}>
                          <label className="form-label">{lbl}</label>
                          <input className="form-input" value={formData[k]} onChange={ff(k)} placeholder={lbl} />
                        </div>
                      ))}
                    </div>
                  </fieldset>

                  {/* Research */}
                  <fieldset style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-md)', padding: '1.1rem' }}>
                    <legend style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '.8125rem', padding: '0 .4rem' }}>Research</legend>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
                      <div className="form-group">
                        <label className="form-label">Research interests <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(one per line)</span></label>
                        <textarea className="form-textarea" value={formData.research_interests} onChange={ff('research_interests')} placeholder={"Computer Vision\nDeep Learning\nNatural Language Processing"} rows={4} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Areas evidenced by your work <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(one per line)</span></label>
                        <textarea className="form-textarea" value={formData.signals} onChange={ff('signals')} placeholder={"Medical AI\nEdge AI"} rows={3} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Skills <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(one per line; optional type after "|": language, framework, ml_tool, database, cloud, other)</span></label>
                        <textarea className="form-textarea" value={formData.skills} onChange={ff('skills')} placeholder={"Python | language\nPyTorch | ml_tool\nPostgreSQL | database"} rows={4} />
                      </div>
                    </div>
                  </fieldset>

                  {/* Projects / Pubs / Experience */}
                  <ItemListEditor
                    title="Publications"
                    items={formData.publications}
                    fields={PUBLICATION_FIELDS}
                    onChange={list => setFormData(d => ({ ...d, publications: list }))}
                    addLabel="Add publication"
                    emptyItem={{ title: '', venue: '', year: '', authors: '', publication_type: '' }}
                  />
                  <ItemListEditor
                    title="Experience"
                    items={formData.experience}
                    fields={EXPERIENCE_FIELDS}
                    onChange={list => setFormData(d => ({ ...d, experience: list }))}
                    addLabel="Add experience"
                    emptyItem={{ role: '', organization: '', kind: '', years: '', description: '' }}
                  />
                  <ItemListEditor
                    title="Projects"
                    items={formData.projects}
                    fields={PROJECT_FIELDS}
                    onChange={list => setFormData(d => ({ ...d, projects: list }))}
                    addLabel="Add project"
                    emptyItem={{ title: '', description: '', technologies: '' }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '.75rem', marginTop: '1.75rem' }}>
                  <button onClick={() => setStep(1)} style={{
                    padding: '.7rem 1.2rem',
                    background: 'var(--card)',
                    color: 'var(--ink)',
                    border: '1px solid var(--line)',
                    borderRadius: 'var(--r-md)',
                    fontSize: '.875rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}>
                    ← Back
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                      flex: 1,
                      padding: '.7rem',
                      background: 'var(--navy)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 'var(--r-md)',
                      fontSize: '.9375rem',
                      fontWeight: 700,
                      cursor: saving ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '.5rem',
                      opacity: saving ? .7 : 1,
                    }}
                  >
                    {saving ? <><Spinner size={16} color="#fff" /> Saving…</> : 'Save edits →'}
                  </button>
                </div>
              </>
            )}

            {/* ── Step 3: Confirm ───────────────────────── */}
            {step === 3 && (
              <div style={{ textAlign: 'center', padding: '1rem 0' }}>
                {confirmed ? (
                  <>
                    <div style={{
                      width: '64px', height: '64px', borderRadius: '50%',
                      background: 'var(--green-bg)', border: '2px solid var(--green-bdr)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem',
                    }}>
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2.5">
                        <path d="M20 6L9 17l-5-5"/>
                      </svg>
                    </div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '.5rem', fontFamily: 'var(--font-serif)' }}>
                      Profile confirmed!
                    </h2>
                    <p style={{ color: 'var(--muted)', fontSize: '.875rem', marginBottom: '2rem', lineHeight: 1.6 }}>
                      Your research profile is ready. Start discovering professors whose work aligns with yours.
                    </p>
                    <Link
                      to="/matches"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '.4rem',
                        background: 'var(--navy)',
                        color: '#fff',
                        padding: '.8rem 1.75rem',
                        borderRadius: 'var(--r-md)',
                        textDecoration: 'none',
                        fontWeight: 700,
                        fontSize: '.9375rem',
                      }}
                    >
                      Find Matching Professors →
                    </Link>
                    <div style={{ display: 'flex', gap: '.6rem', justifyContent: 'center', marginTop: '1rem', flexWrap: 'wrap' }}>
                      <button type="button" onClick={() => setStep(2)} style={{
                        padding: '.55rem 1rem', background: 'var(--card)', color: 'var(--ink)',
                        border: '1px solid var(--line)', borderRadius: 'var(--r-md)', fontSize: '.8125rem',
                        fontWeight: 500, cursor: 'pointer',
                      }}>
                        Edit profile
                      </button>
                      <button type="button" onClick={startNewUpload} style={{
                        padding: '.55rem 1rem', background: 'var(--card)', color: 'var(--ink)',
                        border: '1px solid var(--line)', borderRadius: 'var(--r-md)', fontSize: '.8125rem',
                        fontWeight: 500, cursor: 'pointer',
                      }}>
                        Upload a new CV
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{
                      width: '64px', height: '64px', borderRadius: '50%',
                      background: 'var(--accent-bg)', border: '2px solid var(--accent-bdr)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem',
                    }}>
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
                        <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2"/>
                      </svg>
                    </div>
                    <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '.5rem', fontFamily: 'var(--font-serif)' }}>
                      Confirm your profile
                    </h2>
                    <p style={{ color: 'var(--muted)', fontSize: '.875rem', marginBottom: '1.75rem', lineHeight: 1.6 }}>
                      By confirming, you're ready for research matching. You can always edit your profile later.
                    </p>
                    <div style={{ display: 'flex', gap: '.75rem', justifyContent: 'center' }}>
                      <button onClick={() => setStep(2)} style={{
                        padding: '.7rem 1.2rem',
                        background: 'var(--card)',
                        color: 'var(--ink)',
                        border: '1px solid var(--line)',
                        borderRadius: 'var(--r-md)',
                        fontSize: '.875rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}>
                        ← Edit profile
                      </button>
                      <button
                        onClick={handleConfirm}
                        disabled={confirming}
                        style={{
                          padding: '.7rem 1.5rem',
                          background: 'var(--navy)',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 'var(--r-md)',
                          fontSize: '.9375rem',
                          fontWeight: 700,
                          cursor: confirming ? 'not-allowed' : 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '.5rem',
                          opacity: confirming ? .7 : 1,
                        }}
                      >
                        {confirming ? <><Spinner size={16} color="#fff" /> Confirming…</> : 'Confirm profile'}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
