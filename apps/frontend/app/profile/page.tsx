'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { deleteAccount, findMatches, getCurrentUser, getUserState, logoutUser, patchUserState, submitRecommendation } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Avatar } from '@/components/ProfessorCard';
import { ChipInput } from '@/components/Filters';
import { Icon } from '@/components/Icon';
import { Toast } from '@/components/Toast';
import { localStore } from '@/lib/local-store';
import type { LocalUser, StudentProfile } from '@/lib/types';

const defaultProfile: StudentProfile = {
  name: '',
  photo_url: '',
  email: '',
  target_degree: 'PhD',
  target_department: '',
  highest_degree: { degree: '', field: '', institution: '', year: '' },
  background: '',
  academic_background: '',
  research_interests: '',
  interest_tags: [],
  interests_free_text: '',
  preferred_departments: [],
  preferred_universities: [],
  preferred_locations: [],
  limit: 10,
  shortlist_limit: 50,
  rerank: false,
  include_publication_evidence: true,
  max_abstracts_per_professor: 10,
};

function listToText(value?: string[]) {
  return (value || []).join(', ');
}

function resizeImageToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!['image/jpeg', 'image/png'].includes(file.type)) return reject(new Error('Upload a JPG or PNG image.'));
    if (file.size > 2 * 1024 * 1024) return reject(new Error('Photo must be 2MB or smaller.'));
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read photo.'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('Could not process photo.'));
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const size = 256;
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        if (!ctx) return reject(new Error('Could not process photo.'));
        const side = Math.min(img.width, img.height);
        const sx = (img.width - side) / 2;
        const sy = (img.height - side) / 2;
        ctx.drawImage(img, sx, sy, side, side, 0, 0, size, size);
        resolve(canvas.toDataURL(file.type === 'image/png' ? 'image/png' : 'image/jpeg', 0.86));
      };
      img.src = String(reader.result);
    };
    reader.readAsDataURL(file);
  });
}

function normalizeProfile(profile: StudentProfile): StudentProfile {
  const background = profile.academic_background || profile.background || '';
  const tagsText = listToText(profile.interest_tags);
  return {
    ...defaultProfile,
    ...profile,
    background,
    academic_background: background,
    research_interests: tagsText || profile.research_interests,
    interests_free_text: '',
    highest_degree: { ...defaultProfile.highest_degree, ...(profile.highest_degree || {}) },
    preferred_departments: profile.preferred_departments || (profile.target_department ? [profile.target_department] : []),
  };
}

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<LocalUser | null>(null);
  const [profile, setProfile] = useState<StudentProfile>(defaultProfile);
  const [initial, setInitial] = useState<StudentProfile>(defaultProfile);
  const [interestTags, setInterestTags] = useState<string[]>([]);
  const [preferredUniversities, setPreferredUniversities] = useState<string[]>([]);
  const [preferredLocations, setPreferredLocations] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [toast, setToast] = useState('');
  const [saving, setSaving] = useState(false);
  const [recommendOpen, setRecommendOpen] = useState(false);
  const [recommendForm, setRecommendForm] = useState({ university: '', department: '', faculty_page_url: '' });
  const [recommendSubmitting, setRecommendSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    const localUser = localStore.getUser();
    setUser(localUser);
    const localProfile = localStore.getProfile();
    if (localProfile) {
      const normalized = normalizeProfile(localProfile);
      setProfile(normalized);
      setInitial(normalized);
      setInterestTags(normalized.interest_tags || []);
      setPreferredUniversities(normalized.preferred_universities || []);
      setPreferredLocations(normalized.preferred_locations || []);
    }

    getCurrentUser().then(response => {
      const restored = { name: response.user.display_name, email: response.user.email, createdAt: response.user.created_at, role: response.user.role, photo_url: localProfile?.photo_url };
      localStore.setUser(restored);
      setUser(restored);
      setProfile(p => ({ ...p, name: p.name || restored.name, email: p.email || restored.email }));
    }).catch(() => undefined);

    getUserState().then(state => {
      if (state.student_profile) {
        const normalized = normalizeProfile(state.student_profile);
        localStore.setProfile(normalized);
        setProfile(normalized);
        setInitial(normalized);
        setInterestTags(normalized.interest_tags || []);
        setPreferredUniversities(normalized.preferred_universities || []);
        setPreferredLocations(normalized.preferred_locations || []);
      }
    }).catch(() => undefined);
  }, []);

  const composedProfile = useMemo(() => normalizeProfile({
    ...profile,
    interest_tags: interestTags,
    preferred_universities: preferredUniversities,
    preferred_locations: preferredLocations,
  }), [profile, interestTags, preferredUniversities, preferredLocations]);

  const dirty = JSON.stringify(composedProfile) !== JSON.stringify(initial);

  useEffect(() => {
    if (!recommendOpen || recommendSubmitting) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setRecommendOpen(false);
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [recommendOpen, recommendSubmitting]);

  function update<K extends keyof StudentProfile>(key: K, value: StudentProfile[K]) {
    setProfile(current => ({ ...current, [key]: value }));
  }

  async function saveProfile(runMatch: boolean) {
    setError('');
    setSuccess('');
    const profileToSave = normalizeProfile({
      ...profile,
      interest_tags: interestTags,
      preferred_universities: preferredUniversities,
      preferred_locations: preferredLocations,
    });
    if (!profileToSave.name.trim() || !profileToSave.email?.trim()) {
      return setError('Add your name and email before saving.');
    }
    if (!profileToSave.interest_tags?.length) {
      return setError('Add at least one area of interest tag.');
    }
    setSaving(true);
    try {
      localStore.setProfile(profileToSave);
      const nextUser = user ? { ...user, name: profileToSave.name || user.name, photo_url: profileToSave.photo_url } : null;
      if (nextUser) { localStore.setUser(nextUser); setUser(nextUser); }
      await patchUserState({ student_profile: profileToSave });
      setInitial(profileToSave);
      if (runMatch) {
        const matchResponse = await findMatches(profileToSave);
        localStore.setMatches(matchResponse);
        await patchUserState({ last_match_response: matchResponse });
        setToast('Profile saved and matches refreshed.');
        setTimeout(() => router.push('/match'), 450);
      } else {
        setSuccess('Profile updated.');
        setToast('Profile saved.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update profile.');
    } finally {
      setSaving(false);
    }
  }

  async function submitRecommendationRequest(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!recommendForm.university.trim() || !recommendForm.department.trim()) return setError('Add both university and department.');
    try {
      const url = new URL(recommendForm.faculty_page_url.trim());
      if (!['http:', 'https:'].includes(url.protocol)) return setError('Faculty page URL must start with http or https.');
    } catch {
      return setError('Enter a valid faculty page URL.');
    }
    setRecommendSubmitting(true);
    try {
      await submitRecommendation({ university: recommendForm.university.trim(), department: recommendForm.department.trim(), faculty_page_url: recommendForm.faculty_page_url.trim() });
      setRecommendForm({ university: '', department: '', faculty_page_url: '' });
      setRecommendOpen(false);
      setSuccess('Recommendation submitted.');
      setToast('University and department recommended.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit recommendation.');
    } finally {
      setRecommendSubmitting(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await saveProfile(false);
  }

  async function handlePhotoUpload(file?: File) {
    if (!file) return;
    setError('');
    try {
      const photoUrl = await resizeImageToDataUrl(file);
      const nextProfile = { ...profile, photo_url: photoUrl };
      update('photo_url', photoUrl);
      localStore.setProfile(normalizeProfile(nextProfile));
      if (user) {
        const nextUser = { ...user, photo_url: photoUrl };
        localStore.setUser(nextUser);
        setUser(nextUser);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not upload photo.');
    }
  }

  async function handleDeleteAccount() {
    setDeleting(true);
    try {
      await deleteAccount();
    } catch {
      await logoutUser().catch(() => undefined);
    }
    localStore.clearPrivateState();
    router.push('/');
  }

  return (
    <div className="page profile-page">
      <div className="card soft row between" style={{ marginBottom: 18 }}>
        <div>
          <h3>Don’t see who you’re looking for?</h3>
          <p className="muted">Recommend universities and departments so they can be added to Professor Match.</p>
        </div>
        <button className="button primary" type="button" onClick={() => setRecommendOpen(true)}><Icon name="plus" size={14} />Recommend Universities and Departments</button>
      </div>

      <div className="row between" style={{ marginBottom: 22 }}>
        <div>
          <h2>Academic profile</h2>
          <p className="muted">Keep this current so your professor matches reflect your latest goals.</p>
        </div>
        {user && <span className="badge profile-badge"><Avatar name={user.name} photoUrl={user.photo_url || profile.photo_url} /> Signed in as {user.name}</span>}
      </div>

      {error && <div className="error" style={{ marginBottom: 14 }}>{error}</div>}
      {success && <div className="notice" style={{ marginBottom: 14 }}>{success}</div>}

      <form className="form" onSubmit={submit}>
        <section className="card form-section">
          <h3>Basic information</h3>
          <div className="form-grid">
            <label className="label">Name<input className="input" value={profile.name} onChange={e => update('name', e.target.value)} placeholder="Jordan Lee" /></label>
            <label className="label">Email<input className="input" type="email" value={profile.email || ''} onChange={e => update('email', e.target.value)} placeholder="you@university.edu" /></label>
            <div className="label photo-upload">Profile photo
              <label className="photo-dropzone">
                <Avatar name={profile.name || 'Applicant'} photoUrl={profile.photo_url} />
                <span><strong>Upload a profile photo</strong><small>JPG or PNG</small></span>
                <em>Browse</em>
                <input type="file" accept="image/jpeg,image/png" onChange={e => handlePhotoUpload(e.target.files?.[0])} />
              </label>
            </div>
            <label className="label">Target Degree<input className="input" value={profile.target_degree} onChange={e => update('target_degree', e.target.value)} placeholder="PhD" /></label>
            <label className="label">Department<input className="input" value={profile.target_department || ''} onChange={e => update('target_department', e.target.value)} placeholder="Computer Science" /></label>
          </div>
        </section>

        <section className="card form-section">
          <h3>Highest degree attained</h3>
          <div className="form-grid">
            <label className="label">Degree<input className="input" value={profile.highest_degree?.degree || ''} onChange={e => update('highest_degree', { ...profile.highest_degree, degree: e.target.value })} placeholder="BS" /></label>
            <label className="label">Field<input className="input" value={profile.highest_degree?.field || ''} onChange={e => update('highest_degree', { ...profile.highest_degree, field: e.target.value })} placeholder="Computer Science" /></label>
            <label className="label">Institution<input className="input" value={profile.highest_degree?.institution || ''} onChange={e => update('highest_degree', { ...profile.highest_degree, institution: e.target.value })} placeholder="Your university" /></label>
            <label className="label">Year<input className="input" value={profile.highest_degree?.year || ''} onChange={e => update('highest_degree', { ...profile.highest_degree, year: e.target.value })} placeholder="2025" /></label>
          </div>
        </section>

        <section className="card form-section" id="areas-of-interest">
          <h3>Research fit</h3>
          <div className="form-grid">
            <ChipInput label="Areas of Interest" values={interestTags} onChange={setInterestTags} placeholder="Type comma-separated interests" />
            <ChipInput label="Preferred Universities" values={preferredUniversities} onChange={setPreferredUniversities} placeholder="Type a university, press Enter" />
            <ChipInput label="Preferred Locations" values={preferredLocations} onChange={setPreferredLocations} placeholder="Type a location, press Enter" />
          </div>
          <label className="label">Academic Background<textarea className="textarea" value={profile.academic_background || profile.background || ''} onChange={e => { update('academic_background', e.target.value); update('background', e.target.value); }} placeholder="Summarize coursework, research, publications, work experience, and skills." /></label>
        </section>

        <div className="profile-save-bar row between">
          <p className="muted small-text">Save small edits now, or save and refresh your matches.</p>
          <div className="row end profile-action-group">
            {saving && <span className="inline-saving" role="status" aria-live="polite"><i />Saving…</span>}
            <button className="button secondary" type="submit" disabled={saving}>{dirty ? 'Update profile' : 'Save profile'}</button>
            <button className="button primary" type="button" disabled={saving} onClick={() => saveProfile(true)}>Update and match</button>
          </div>
        </div>
      </form>

      <div className="danger-zone">
        <button className="button danger-primary" onClick={() => setConfirmDelete(true)} disabled={deleting}><Icon name="trash" size={13} />{deleting ? 'Deleting…' : 'Delete account'}</button>
      </div>
      {recommendOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => !recommendSubmitting && setRecommendOpen(false)}>
          <form className="modal-card form" role="dialog" aria-modal="true" aria-labelledby="recommend-title" onMouseDown={event => event.stopPropagation()} onSubmit={submitRecommendationRequest}>
            <div className="modal-icon"><Icon name="plus" size={16} /></div>
            <h3 id="recommend-title">Recommend a university or department</h3>
            <p className="muted small-text">Tell us which faculty directory should be considered next.</p>
            <label className="label">University<input className="input" value={recommendForm.university} onChange={e => setRecommendForm(f => ({ ...f, university: e.target.value }))} placeholder="University name" required /></label>
            <label className="label">Department<input className="input" value={recommendForm.department} onChange={e => setRecommendForm(f => ({ ...f, department: e.target.value }))} placeholder="Computer Science" required /></label>
            <label className="label">Faculty Page URL<input className="input" type="url" value={recommendForm.faculty_page_url} onChange={e => setRecommendForm(f => ({ ...f, faculty_page_url: e.target.value }))} placeholder="https://example.edu/cs/faculty" required /></label>
            <div className="row end">
              <button className="button secondary" type="button" onClick={() => setRecommendOpen(false)}>Cancel</button>
              <button className="button primary" type="submit" disabled={recommendSubmitting}>{recommendSubmitting ? 'Submitting…' : 'Submit recommendation'}</button>
            </div>
          </form>
        </div>
      )}
      <Toast message={toast} onClose={() => setToast('')} />
      <ConfirmDialog
        open={confirmDelete}
        variant="danger"
        title="Delete account?"
        message="This will sign you out and disable this profile. This action cannot be undone."
        confirmLabel="Delete account"
        confirming={deleting}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={handleDeleteAccount}
      />
    </div>
  );
}
