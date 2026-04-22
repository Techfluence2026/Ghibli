import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/client';
import { User, Save, Loader, CheckCircle } from 'lucide-react';
import './Profile.css';

const GENDERS = ['male', 'female', 'other'];
const BLOOD_GROUPS = ['A+', 'A-', 'b+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({
    age: '', gender: '', height: '', weight: '', blood_group: '',
    medical_history: '', allergies: '', timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (user) {
      setForm({
        age: user.age ?? '',
        gender: user.gender ?? '',
        height: user.height ?? '',
        weight: user.weight ?? '',
        blood_group: user.blood_group ?? '',
        medical_history: user.medical_history ?? '',
        allergies: Array.isArray(user.allergies) ? user.allergies.join(', ') : (user.allergies ?? ''),
        timezone: user.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
    }
  }, [user]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    setSaved(false);

    const allergiesList = form.allergies
      ? form.allergies.split(',').map((s) => s.trim()).filter(Boolean)
      : [];

    const payload = {
      id: user.id,
      age: parseInt(form.age, 10),
      gender: form.gender,
      height: parseFloat(form.height),
      weight: parseFloat(form.weight),
      blood_group: form.blood_group,
      medical_history: form.medical_history || null,
      allergies: allergiesList.length > 0 ? allergiesList : null,
      timezone: form.timezone,
    };

    // Validate required fields
    if (!payload.age || !payload.gender || !payload.height || !payload.weight || !payload.blood_group) {
      setError('Age, Gender, Height, Weight, and Blood Group are required.');
      setSaving(false);
      return;
    }

    try {
      await authAPI.updateUserDetails(payload);
      await refreshUser();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === 'string' ? msg : (Array.isArray(msg) ? msg.map((m) => m.msg).join(', ') : 'Save failed.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-content">
      <h1 className="page-title">Profile</h1>
      <p className="page-subtitle">Manage your personal health information.</p>

      <div className="profile-layout">
        {/* Left: identity card */}
        <div className="profile-identity card">
          <div className="profile-avatar-lg">
            {user?.username?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <h2 className="profile-name">{user?.username ?? '—'}</h2>
          <p className="profile-email">{user?.email ?? '—'}</p>
          <p className="profile-phone">{user?.phone ?? '—'}</p>

          <div className="divider" />

          <div className="profile-pills">
            {user?.blood_group && (
              <span className="badge badge-danger">{user.blood_group}</span>
            )}
            {user?.gender && (
              <span className="badge badge-primary" style={{ textTransform: 'capitalize' }}>{user.gender}</span>
            )}
            {user?.age && (
              <span className="badge badge-neutral">Age {user.age}</span>
            )}
          </div>

          {(user?.medical_history || (user?.diseases?.length > 0)) && (
            <div className="profile-history">
              <div className="profile-history-label">Medical History</div>
              <p>{user.medical_history}</p>
              {user?.diseases?.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {user.diseases.map((d, i) => (
                    <span key={i} className="badge badge-warning">{d}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          {user?.allergies?.length > 0 && (
            <div className="profile-history">
              <div className="profile-history-label">Allergies</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {user.allergies.map((a, i) => <span key={i} className="badge badge-danger">{a}</span>)}
              </div>
            </div>
          )}
        </div>

        {/* Right: edit form */}
        <div className="profile-form-panel card">
          <h2 className="section-title" style={{ marginBottom: 'var(--space-6)' }}>
            <User size={18} style={{ display: 'inline', marginRight: 8, verticalAlign: 'middle' }} />
            Health Details
          </h2>

          {error && (
            <div className="auth-alert auth-alert--error" style={{ marginBottom: 'var(--space-5)' }}>
              {error}
            </div>
          )}

          {saved && (
            <div className="auth-alert auth-alert--success" style={{ marginBottom: 'var(--space-5)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle size={16} /> Profile updated successfully!
            </div>
          )}

          <form onSubmit={handleSave} className="profile-form">
            <div className="profile-form-row">
              <div className="form-group">
                <label className="form-label" htmlFor="profile-age">Age *</label>
                <input
                  id="profile-age"
                  className="form-input"
                  type="number"
                  min="1"
                  max="120"
                  placeholder="e.g. 30"
                  value={form.age}
                  onChange={set('age')}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="profile-gender">Gender *</label>
                <select
                  id="profile-gender"
                  className="form-input form-select"
                  value={form.gender}
                  onChange={set('gender')}
                  required
                >
                  <option value="">Select gender</option>
                  {GENDERS.map((g) => (
                    <option key={g} value={g} style={{ textTransform: 'capitalize' }}>{g}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="profile-form-row">
              <div className="form-group">
                <label className="form-label" htmlFor="profile-height">Height (cm) *</label>
                <input
                  id="profile-height"
                  className="form-input"
                  type="number"
                  min="50"
                  max="300"
                  step="0.1"
                  placeholder="e.g. 175"
                  value={form.height}
                  onChange={set('height')}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="profile-weight">Weight (kg) *</label>
                <input
                  id="profile-weight"
                  className="form-input"
                  type="number"
                  min="1"
                  max="500"
                  step="0.1"
                  placeholder="e.g. 70"
                  value={form.weight}
                  onChange={set('weight')}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="profile-blood-group">Blood Group *</label>
              <select
                id="profile-blood-group"
                className="form-input form-select"
                value={form.blood_group}
                onChange={set('blood_group')}
                required
              >
                <option value="">Select blood group</option>
                {BLOOD_GROUPS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="profile-allergies">
                Allergies
                <span className="profile-field-hint"> (comma-separated)</span>
              </label>
              <input
                id="profile-allergies"
                className="form-input"
                type="text"
                placeholder="e.g. Penicillin, Peanuts"
                value={form.allergies}
                onChange={set('allergies')}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="profile-history">Medical History</label>
              <textarea
                id="profile-history"
                className="form-textarea"
                placeholder="Any past conditions, surgeries, chronic illnesses…"
                value={form.medical_history}
                onChange={set('medical_history')}
                rows={4}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="profile-timezone">
                Timezone
                <span className="profile-field-hint"> (For medication reminders)</span>
              </label>
              <input
                id="profile-timezone"
                className="form-input"
                type="text"
                placeholder="e.g. America/New_York"
                value={form.timezone}
                onChange={set('timezone')}
                required
              />
            </div>

            <button
              type="submit"
              id="profile-save-btn"
              className="btn btn-primary"
              disabled={saving}
              style={{ width: 'fit-content', alignSelf: 'flex-end' }}
            >
              {saving
                ? <><Loader size={16} className="spin" /> Saving…</>
                : <><Save size={16} /> Save Changes</>
              }
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
