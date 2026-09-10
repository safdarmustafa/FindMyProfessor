import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AppShell from '../components/AppShell/AppShell.jsx';
import Spinner from '../components/Spinner.jsx';
import { uploadCV, fetchProfile, updateProfile, confirmProfile } from '../services/profile.js';
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
function parseList(text) {
  if (!text) return [];
  return text.split('\n').map(s => s.trim()).filter(Boolean);
}

function parseSkills(text) {
  if (!text) return [];
  return parseList(text).map(line => {
    const parts = line.split('|');
    return { name: parts[0]?.trim(), category: parts[1]?.trim() || 'general' };
  });
}

function tryParseJSON(text) {
  if (!text || !text.trim()) return [];
  try { return JSON.parse(text); } catch { return text; }
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
    projects: '', publications: '', experience: '',
  });
  const [saving, setSaving] = useState(false);

  // Step 3
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    const profileId = getProfileId();
    if (!profileId) return;
    setLoading(true);
    fetchProfile()
      .then(data => {
        setProfile(data);
        if (data.extracted_profile) {
          populateForm(data.extracted_profile);
        }
        if (data.confirmed) {
          setStep(3);
          setConfirmed(true);
        } else if (data.extracted_profile) {
          setStep(2);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function populateForm(ep) {
    const identity = ep.identity || ep;
    const education = (ep.education || [])[0] || {};
    const research = ep.research || {};
    setFormData({
      name: identity.name || '',
      email: identity.email || '',
      phone: identity.phone || '',
      degree: education.degree || '',
      field: education.field || '',
      institution: education.institution || '',
      country: education.country || '',
      grad_year: education.grad_year || education.year || '',
      semester: education.semester || '',
      research_interests: (research.interests || []).join('\n'),
      signals: (research.signals || []).join('\n'),
      skills: (ep.skills || []).map(s => typeof s === 'string' ? s : `${s.name} | ${s.category || 'general'}`).join('\n'),
      projects: ep.projects ? JSON.stringify(ep.projects, null, 2) : '',
      publications: ep.publications ? JSON.stringify(ep.publications, null, 2) : '',
      experience: ep.experience ? JSON.stringify(ep.experience, null, 2) : '',
    });
  }

  function collectProfile() {
    return {
      identity: { name: formData.name, email: formData.email, phone: formData.phone },
      education: [{
        degree: formData.degree,
        field: formData.field,
        institution: formData.institution,
        country: formData.country,
        grad_year: formData.grad_year,
        semester: formData.semester,
      }],
      research: {
        interests: parseList(formData.research_interests),
        signals: parseList(formData.signals),
      },
      skills: parseSkills(formData.skills),
      projects: tryParseJSON(formData.projects),
      publications: tryParseJSON(formData.publications),
      experience: tryParseJSON(formData.experience),
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
      if (data.extracted_profile) populateForm(data.extracted_profile);
      setStep(2);
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
      setStep(3);
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

          {/* White card wrapper */}
          <div style={{
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
                    onClick={() => setStep(2)}
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
                    Continue with existing profile →
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
                        <label className="form-label">Research signals <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(one per line)</span></label>
                        <textarea className="form-textarea" value={formData.signals} onChange={ff('signals')} placeholder="Published paper on transformer architectures" rows={3} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Skills <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(format: Python | language)</span></label>
                        <textarea className="form-textarea" value={formData.skills} onChange={ff('skills')} placeholder={"Python | language\nPyTorch | framework\nResearch | methodology"} rows={4} />
                      </div>
                    </div>
                  </fieldset>

                  {/* Projects / Pubs / Experience */}
                  {[
                    ['projects','Projects (JSON)'], ['publications','Publications (JSON)'], ['experience','Experience (JSON)'],
                  ].map(([k, lbl]) => (
                    <div key={k} className="form-group">
                      <label className="form-label">{lbl}</label>
                      <textarea className="form-textarea" value={formData[k]} onChange={ff(k)} rows={4} style={{ fontFamily: 'monospace', fontSize: '.8125rem' }} />
                    </div>
                  ))}
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
