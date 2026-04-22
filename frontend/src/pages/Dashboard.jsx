import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { reportsAPI, medicationsAPI } from '../api/client';
import { getAlerts, formatDate, analyzeTest, severityClass } from '../api/health';
import {
  AlertTriangle, FileText, Upload, ChevronRight, Loader, Pill, Trash2, Plus, Clock
} from 'lucide-react';
import './Dashboard.css';

function StatCard({ label, value, sub, icon: Icon, color }) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon" style={{ background: `${color}18`, color }}>
        <Icon size={20} />
      </div>
      <div className="stat-card-body">
        <div className="stat-card-value">{value}</div>
        <div className="stat-card-label">{label}</div>
        {sub && <div className="stat-card-sub">{sub}</div>}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [reports, setReports] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    reportsAPI.getAll({ limit: 100 })
      .then((data) => {
        const sorted = [...data].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setReports(sorted);
        setAlerts(getAlerts(sorted));
      })
      .catch((e) => setError(e?.response?.data?.detail || 'Failed to load reports.'))
      .finally(() => setLoading(false));
  }, []);

  const criticalCount = alerts.filter((a) => a.severity === 'critical').length;

  return (
    <div className="page-content">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1 className="page-title">
            Good {getGreeting()}, {user?.username?.split(' ')[0] ?? 'there'} 👋
          </h1>
          <p className="page-subtitle">Here's a summary of your health data.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/upload')} id="dashboard-upload-btn">
          <Upload size={16} /> Upload Report
        </button>
      </div>

      {error && (
        <div className="auth-alert auth-alert--error" style={{ marginBottom: 'var(--space-6)' }}>
          {error}
        </div>
      )}

      {/* Stats Row */}
      <div className="stats-grid stats-grid--3col">
        <StatCard
          label="Total Reports"
          value={loading ? '—' : reports.length}
          sub="All time"
          icon={FileText}
          color="var(--primary)"
        />
        <StatCard
          label="Active Alerts"
          value={loading ? '—' : alerts.length}
          sub={criticalCount > 0 ? `${criticalCount} critical` : 'All normal ranges'}
          icon={AlertTriangle}
          color={alerts.length > 0 ? 'var(--danger)' : 'var(--success)'}
        />
        <StatCard
          label="Reports Analysed"
          value={loading ? '—' : reports.filter((r) => r.tests?.length > 0).length}
          sub="With extracted data"
          icon={FileText}
          color="var(--success)"
        />
      </div>

      {/* Single column layout */}
      <div className="dashboard-single">
        {/* Health alerts */}
        <div className="card">
          <div className="section-header">
            <h2 className="section-title">🚨 Health Alerts</h2>
            <span className="badge badge-danger">{alerts.length} alerts</span>
          </div>

          {loading && <SkeletonList rows={3} />}

          {!loading && alerts.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <h3>All values in normal range</h3>
              <p>Upload a report to start tracking your health metrics.</p>
            </div>
          )}

          {!loading && alerts.length > 0 && (
            <div className="alert-list">
              {alerts.slice(0, 6).map((a, i) => (
                <div key={i} className={`alert-row alert-row--${a.severity}`}>
                  <div className="alert-row-left">
                    <AlertTriangle size={16} className={`alert-icon alert-icon--${a.severity}`} />
                    <div>
                      <div className="alert-name">{a.testName}</div>
                      <div className="alert-meta">
                        {a.value} {a.unit}
                        {a.referenceRange && ` · Ref: ${a.referenceRange}`}
                      </div>
                      <div className="alert-report-ref">Report · {formatDate(a.reportDate)}</div>
                    </div>
                  </div>
                  <span className={`badge ${severityClass(a.severity)}`}>{a.label}</span>
                </div>
              ))}
              {alerts.length > 6 && (
                <button className="btn btn-ghost btn-sm" onClick={() => navigate('/analytics')} style={{ marginTop: 8 }}>
                  View all {alerts.length} →
                </button>
              )}
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="card">
          <div className="section-header">
            <h2 className="section-title">🕒 Report Timeline</h2>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/records')}>
              View all <ChevronRight size={14} />
            </button>
          </div>

          {loading && <SkeletonList rows={4} />}

          {!loading && reports.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon"><FileText size={24} /></div>
              <h3>No reports yet</h3>
              <p>Upload your first report to see your health timeline.</p>
              <button className="btn btn-primary btn-sm" onClick={() => navigate('/upload')}>
                <Upload size={14} /> Upload Now
              </button>
            </div>
          )}

          {!loading && reports.length > 0 && (
            <div className="timeline">
              {reports.slice(0, 5).map((r) => {
                const reportAlerts = getAlerts([r]);
                return (
                  <div
                    key={r.id}
                    className="timeline-item"
                    onClick={() => navigate('/records')}
                  >
                    <div className="timeline-dot" />
                    <div className="timeline-content">
                      <div className="timeline-top">
                        <span className="timeline-patient">{r.patient_name}</span>
                        <span className="timeline-date">{formatDate(r.created_at)}</span>
                      </div>
                      <div className="timeline-status-row">
                        <span className={`badge badge-${statusBadge(r.status)}`}>{r.status}</span>
                        {reportAlerts.length > 0 && (
                          <span className="badge badge-danger">{reportAlerts.length} alert{reportAlerts.length > 1 ? 's' : ''}</span>
                        )}
                        {r.doctor && <span className="timeline-doctor">Dr. {r.doctor}</span>}
                      </div>
                      {r.tests?.length > 0 && (
                        <div className="timeline-tests">
                          {r.tests.slice(0, 3).map((t, ti) => {
                            const anomaly = analyzeTest(t);
                            return (
                              <span key={ti} className={`timeline-test-tag ${anomaly ? `timeline-test-tag--${anomaly.severity}` : ''}`}>
                                {t.name}: {t.result} {t.unit}
                              </span>
                            );
                          })}
                          {r.tests.length > 3 && <span className="timeline-test-tag">+{r.tests.length - 3} more</span>}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Summary generator */}
        <SummaryCard reports={reports} loading={loading} />
        
        {/* Medications Card */}
        <MedicationsCard />
      </div>
    </div>
  );
}

function MedicationsCard() {
  const [meds, setMeds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newMed, setNewMed] = useState({ name: '', dose: '', times: '' });

  useEffect(() => {
    loadMeds();
  }, []);

  const loadMeds = () => {
    setLoading(true);
    medicationsAPI.getAll()
      .then(setMeds)
      .catch((e) => console.error('Failed to load meds:', e))
      .finally(() => setLoading(false));
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newMed.name || !newMed.dose || !newMed.times) return;

    // split times by comma and trim
    const timesArray = newMed.times.split(',').map(t => t.trim()).filter(Boolean);
    
    try {
      await medicationsAPI.add({
        name: newMed.name,
        dose: newMed.dose,
        times: timesArray
      });
      setShowForm(false);
      setNewMed({ name: '', dose: '', times: '' });
      loadMeds();
    } catch (e) {
      console.error('Failed to add med:', e);
    }
  };

  const handleDelete = async (id) => {
    try {
      await medicationsAPI.delete(id);
      setMeds(meds.filter(m => m.id !== id));
    } catch (e) {
      console.error('Failed to delete med:', e);
    }
  };

  return (
    <div className="card">
      <div className="section-header">
        <h2 className="section-title"><Pill size={18} style={{ marginRight: 8 }} /> My Medications</h2>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowForm(!showForm)}>
          <Plus size={14} /> Add New
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="auth-form" style={{ marginBottom: 20, padding: 15, background: 'var(--bg-secondary)', borderRadius: 'var(--radius)' }}>
          <div className="form-group">
            <label>Medication Name</label>
            <input type="text" className="input" placeholder="e.g. Amoxicillin" value={newMed.name} onChange={e => setNewMed({...newMed, name: e.target.value})} required />
          </div>
          <div className="form-group">
            <label>Dose</label>
            <input type="text" className="input" placeholder="e.g. 500mg" value={newMed.dose} onChange={e => setNewMed({...newMed, dose: e.target.value})} required />
          </div>
          <div className="form-group">
            <label>Times (comma separated HH:MM)</label>
            <input type="text" className="input" placeholder="e.g. 08:00, 20:00" value={newMed.times} onChange={e => setNewMed({...newMed, times: e.target.value})} required />
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Save Medication</button>
            <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <SkeletonList rows={2} />
      ) : meds.length === 0 ? (
        <div className="empty-state">
           <div className="empty-state-icon"><Pill size={24} /></div>
           <h3>No Medications Scheduled</h3>
           <p>Add your medications to receive WhatsApp reminders.</p>
        </div>
      ) : (
        <div className="alert-list">
          {meds.map(med => (
            <div key={med.id} className="alert-row">
              <div className="alert-row-left">
                <Pill size={16} className="alert-icon alert-icon--primary" />
                <div>
                  <div className="alert-name">{med.name}</div>
                  <div className="alert-meta">{med.dose}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
                <span className="badge badge-primary" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Clock size={12} /> {med.times.join(', ')}
                </span>
                <button className="btn btn-ghost btn-sm" onClick={() => handleDelete(med.id)} title="Delete" style={{ padding: 4, color: 'var(--danger)' }}>
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ reports, loading }) {
  const [summary, setSummary] = useState('');
  const [generating, setGenerating] = useState(false);

  const generate = () => {
    if (!reports.length) return;
    setGenerating(true);

    setTimeout(() => {
      const allAlerts = getAlerts(reports);
      const critical = allAlerts.filter((a) => a.severity === 'critical');
      const high = allAlerts.filter((a) => a.severity === 'high');
      const low = allAlerts.filter((a) => a.severity === 'low');
      const totalTests = reports.reduce((sum, r) => sum + (r.tests?.length ?? 0), 0);

      let text = `📋 Summary based on ${reports.length} report${reports.length > 1 ? 's' : ''} with ${totalTests} lab values.\n\n`;

      if (allAlerts.length === 0) {
        text += '✅ All values appear within normal reference ranges. Keep maintaining a healthy lifestyle.\n';
      } else {
        if (critical.length > 0) {
          text += `🔴 Critical: ${critical.map((a) => `${a.testName} (${a.value} ${a.unit})`).join(', ')}. Immediate medical attention recommended.\n\n`;
        }
        if (high.length > 0) {
          text += `🟡 Elevated: ${high.map((a) => a.testName).join(', ')}. Consider lifestyle adjustments and follow-up screening.\n\n`;
        }
        if (low.length > 0) {
          text += `🟡 Low: ${low.map((a) => a.testName).join(', ')}. Nutritional deficiencies or other factors may be involved.\n\n`;
        }
        text += '⚠️ This is an informational summary only. Please consult a qualified healthcare professional.';
      }

      setSummary(text);
      setGenerating(false);
    }, 800);
  };

  return (
    <div className="card">
      <div className="section-header">
        <h2 className="section-title">📄 Health Summary</h2>
      </div>
      {summary ? (
        <div className="summary-text">{summary}</div>
      ) : (
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: 'var(--space-4)' }}>
          Generate an AI-powered health snapshot from your report data.
        </p>
      )}
      <button
        className="btn btn-primary btn-sm"
        onClick={generate}
        disabled={generating || loading || reports.length === 0}
        id="generate-summary-btn"
      >
        {generating ? <><Loader size={14} className="spin" /> Generating…</> : '✨ Generate Summary'}
      </button>
    </div>
  );
}

function SkeletonList({ rows }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 56, borderRadius: 'var(--radius)' }} />
      ))}
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 18) return 'afternoon';
  return 'evening';
}

function statusBadge(status) {
  const map = { processing: 'warning', pending: 'primary', reviewed: 'success', archived: 'neutral' };
  return map[status] ?? 'neutral';
}
