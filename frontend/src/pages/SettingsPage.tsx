/**
 * SettingsPage - Full-featured settings page for the authenticated user.
 *
 * Sections:
 *  1. Profile          - View/edit full_name (email read-only)
 *  2. Security         - Change password (current + new + confirm)
 *  3. Preferences      - UI prefs persisted to localStorage
 *  4. Scientific Config- ML pipeline defaults (read-only reference)
 *  5. Dataset Info     - Real file availability status from backend
 *  6. System Status    - Live GET /api/health
 *  7. Account          - Logout button
 *  8. Danger Zone      - Account deletion (unavailable notice)
 *  9. Disclaimer       - Scientific / clinical disclaimer
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authApi, healthApi } from '../api/client';
import type { HealthResponse } from '../types';

// Icon helper
const Icon: React.FC<{ path: string; className?: string }> = ({ path, className = 'w-5 h-5' }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={path} />
  </svg>
);

const ICONS = {
  user: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
  lock: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  sliders: 'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4',
  beaker: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
  database: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4',
  activity: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  logout: 'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1',
  alert: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  check: 'M5 13l4 4L19 7',
  eye: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z',
  eyeOff: 'M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21',
  refresh: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
};

// ML Scientific constants mirror ml_service.py
const ML_DEFAULTS = {
  algorithm: 'RandomForest + XGBoost',
  morgan_radius: 2,
  morgan_nbits: 2048,
  random_seed: 42,
  target: 'EGFR / CHEMBL203',
  test_split: '20%',
  validation_split: '10%',
  feature_type: 'Morgan Fingerprints',
};

// Preferences
const PREF_KEY = 'qd_user_prefs';

interface Prefs {
  tableDensity: 'compact' | 'comfortable';
  resultsPerPage: 25 | 50 | 100;
  defaultModel: 'RandomForest' | 'XGBoost';
}

const DEFAULT_PREFS: Prefs = {
  tableDensity: 'comfortable',
  resultsPerPage: 50,
  defaultModel: 'RandomForest',
};

function loadPrefs(): Prefs {
  try {
    const raw = localStorage.getItem(PREF_KEY);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : { ...DEFAULT_PREFS };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

function savePrefs(p: Prefs) {
  localStorage.setItem(PREF_KEY, JSON.stringify(p));
}

// Section card
const SectionCard: React.FC<{
  icon: string;
  title: string;
  subtitle?: string;
  accentColor?: string;
  children: React.ReactNode;
}> = ({ icon, title, subtitle, accentColor = 'text-violet-400', children }) => (
  <div className="glass-card p-0 overflow-hidden">
    <div className="flex items-center gap-3 px-6 py-4 border-b border-white/5">
      <div className={`w-9 h-9 rounded-xl bg-surface-700/80 flex items-center justify-center ${accentColor}`}>
        <Icon path={icon} className="w-4 h-4" />
      </div>
      <div>
        <h2 className="text-white font-semibold text-sm">{title}</h2>
        {subtitle && <p className="text-slate-500 text-xs mt-0.5">{subtitle}</p>}
      </div>
    </div>
    <div className="px-6 py-5">{children}</div>
  </div>
);

// Form input with optional password toggle
const FormInput: React.FC<{
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange?: (v: string) => void;
  readOnly?: boolean;
  placeholder?: string;
  helper?: string;
}> = ({ id, label, type = 'text', value, onChange, readOnly, placeholder, helper }) => {
  const [show, setShow] = useState(false);
  const inputType = type === 'password' ? (show ? 'text' : 'password') : type;

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-xs font-medium text-slate-400 uppercase tracking-wider">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={inputType}
          value={value}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined}
          readOnly={readOnly}
          placeholder={placeholder}
          className={`form-input w-full text-sm ${type === 'password' ? 'pr-10' : ''} ${readOnly ? 'opacity-60 cursor-not-allowed select-none' : ''}`}
        />
        {type === 'password' && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
            aria-label={show ? 'Hide password' : 'Show password'}
          >
            <Icon path={show ? ICONS.eyeOff : ICONS.eye} className="w-4 h-4" />
          </button>
        )}
      </div>
      {helper && <p className="text-slate-600 text-xs">{helper}</p>}
    </div>
  );
};

// Inline alert
const Alert: React.FC<{ type: 'success' | 'error' | 'info'; message: string }> = ({ type, message }) => {
  const styles = {
    success: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
    error: 'bg-red-500/10 border-red-500/30 text-red-400',
    info: 'bg-violet-500/10 border-violet-500/30 text-violet-400',
  };
  return (
    <div className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-xs ${styles[type]}`}>
      <Icon path={type === 'success' ? ICONS.check : ICONS.info} className="w-4 h-4 mt-0.5 flex-shrink-0" />
      <span>{message}</span>
    </div>
  );
};

// Read-only info row
const InfoRow: React.FC<{ label: string; value: string; mono?: boolean }> = ({ label, value, mono }) => (
  <div className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
    <span className="text-slate-500 text-xs">{label}</span>
    <span className={`text-slate-300 text-xs ${mono ? 'font-mono' : 'font-medium'}`}>{value}</span>
  </div>
);

// Pill select
function PillSelect<T extends string | number>({
  id,
  label,
  options,
  value,
  onChange,
}: {
  id: string;
  label: string;
  options: { label: string; value: T }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="space-y-2">
      <span className="block text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
      <div className="flex flex-wrap gap-2" role="group">
        {options.map((opt) => (
          <button
            key={String(opt.value)}
            type="button"
            id={`${id}-${opt.value}`}
            onClick={() => onChange(opt.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 border ${
              value === opt.value
                ? 'bg-violet-600/30 border-violet-500/60 text-violet-300'
                : 'bg-surface-700/60 border-white/5 text-slate-400 hover:text-slate-300 hover:border-white/10'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// Status dot row
const StatusDot: React.FC<{ ok: boolean; label: string }> = ({ ok, label }) => (
  <div className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
    <span className="text-slate-500 text-xs">{label}</span>
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${ok ? 'bg-emerald-400 shadow-sm shadow-emerald-400/40' : 'bg-red-400 shadow-sm shadow-red-400/40'}`} />
      <span className={`text-xs font-medium ${ok ? 'text-emerald-400' : 'text-red-400'}`}>
        {ok ? 'Online' : 'Offline'}
      </span>
    </div>
  </div>
);

// =============================================================
// MAIN PAGE
// =============================================================

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, fetchMe } = useAuthStore();

  // Profile
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [profileStatus, setProfileStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);

  // Security
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwStatus, setPwStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [pwLoading, setPwLoading] = useState(false);

  // Preferences
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs);
  const [prefsSaved, setPrefsSaved] = useState(false);

  // System status
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    if (!user) navigate('/login');
  }, [user, navigate]);

  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(false);
    try {
      const res = await healthApi.check();
      setHealth(res.data as HealthResponse);
    } catch {
      setHealthError(true);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  useEffect(() => {
    setFullName(user?.full_name ?? '');
  }, [user?.full_name]);

  const handleProfileSave = async () => {
    setProfileLoading(true);
    setProfileStatus(null);
    try {
      await authApi.updateMe({ full_name: fullName.trim() || null });
      await fetchMe();
      setProfileStatus({ type: 'success', msg: 'Profile updated successfully.' });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setProfileStatus({ type: 'error', msg: detail ?? 'Failed to update profile.' });
    } finally {
      setProfileLoading(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPw !== confirmPw) {
      setPwStatus({ type: 'error', msg: 'New passwords do not match.' });
      return;
    }
    if (newPw.length < 8) {
      setPwStatus({ type: 'error', msg: 'New password must be at least 8 characters.' });
      return;
    }
    setPwLoading(true);
    setPwStatus(null);
    try {
      await authApi.changePassword({
        current_password: currentPw,
        new_password: newPw,
        confirm_new_password: confirmPw,
      });
      setPwStatus({ type: 'success', msg: 'Password changed successfully.' });
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setPwStatus({ type: 'error', msg: detail ?? 'Failed to change password.' });
    } finally {
      setPwLoading(false);
    }
  };

  const handlePrefChange = <K extends keyof Prefs>(key: K, val: Prefs[K]) => {
    const next = { ...prefs, [key]: val };
    setPrefs(next);
    savePrefs(next);
    setPrefsSaved(true);
    setTimeout(() => setPrefsSaved(false), 2000);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' });

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">

        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
          <p className="text-slate-500 text-sm mt-1">
            Manage your profile, security, and platform preferences.
          </p>
        </div>

        {/* 1. Profile */}
        <SectionCard icon={ICONS.user} title="Profile" subtitle="Your identity on the platform" accentColor="text-violet-400">
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormInput id="settings-username" label="Username" value={user?.username ?? ''} readOnly helper="Username cannot be changed." />
              <FormInput id="settings-email" label="Email" type="email" value={user?.email ?? ''} readOnly helper="Contact support to change your email." />
            </div>
            <FormInput id="settings-fullname" label="Full Name" value={fullName} onChange={setFullName} placeholder="Dr. Jane Smith" />
            {user?.created_at && (
              <p className="text-slate-600 text-xs">Member since {formatDate(user.created_at)}</p>
            )}
            {profileStatus && <Alert type={profileStatus.type} message={profileStatus.msg} />}
            <div className="flex justify-end">
              <button
                id="settings-profile-save"
                onClick={handleProfileSave}
                disabled={profileLoading}
                className="btn-primary text-sm px-5 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {profileLoading ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
          </div>
        </SectionCard>

        {/* 2. Security */}
        <SectionCard icon={ICONS.lock} title="Security" subtitle="Change your account password" accentColor="text-blue-400">
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <FormInput id="settings-current-password" label="Current Password" type="password" value={currentPw} onChange={setCurrentPw} placeholder="Enter current password" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormInput id="settings-new-password" label="New Password" type="password" value={newPw} onChange={setNewPw} placeholder="Min. 8 characters" />
              <FormInput id="settings-confirm-password" label="Confirm New Password" type="password" value={confirmPw} onChange={setConfirmPw} placeholder="Repeat new password" />
            </div>
            {pwStatus && <Alert type={pwStatus.type} message={pwStatus.msg} />}
            <div className="flex justify-end">
              <button
                id="settings-change-password"
                type="submit"
                disabled={pwLoading || !currentPw || !newPw || !confirmPw}
                className="btn-primary text-sm px-5 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {pwLoading ? 'Changing...' : 'Change Password'}
              </button>
            </div>
          </form>
        </SectionCard>

        {/* 3. Preferences */}
        <SectionCard icon={ICONS.sliders} title="Preferences" subtitle="UI settings stored in your browser" accentColor="text-cyan-400">
          <div className="space-y-5">
            <PillSelect
              id="pref-density"
              label="Table Density"
              options={[{ label: 'Compact', value: 'compact' as const }, { label: 'Comfortable', value: 'comfortable' as const }]}
              value={prefs.tableDensity}
              onChange={(v) => handlePrefChange('tableDensity', v)}
            />
            <PillSelect
              id="pref-results"
              label="Results Per Page"
              options={[{ label: '25', value: 25 as const }, { label: '50', value: 50 as const }, { label: '100', value: 100 as const }]}
              value={prefs.resultsPerPage}
              onChange={(v) => handlePrefChange('resultsPerPage', v)}
            />
            <PillSelect
              id="pref-model"
              label="Default Prediction Model"
              options={[{ label: 'RandomForest', value: 'RandomForest' as const }, { label: 'XGBoost', value: 'XGBoost' as const }]}
              value={prefs.defaultModel}
              onChange={(v) => handlePrefChange('defaultModel', v)}
            />
            {prefsSaved && (
              <p className="text-emerald-400 text-xs flex items-center gap-1.5">
                <Icon path={ICONS.check} className="w-3.5 h-3.5" /> Preferences saved automatically.
              </p>
            )}
          </div>
        </SectionCard>

        {/* 4. Scientific Config */}
        <SectionCard icon={ICONS.beaker} title="Scientific Configuration" subtitle="ML pipeline defaults — read-only reference" accentColor="text-indigo-400">
          <div>
            <InfoRow label="Algorithm" value={ML_DEFAULTS.algorithm} />
            <InfoRow label="Feature Type" value={ML_DEFAULTS.feature_type} />
            <InfoRow label="Morgan Fingerprint Radius" value={String(ML_DEFAULTS.morgan_radius)} mono />
            <InfoRow label="Morgan Fingerprint Bits" value={String(ML_DEFAULTS.morgan_nbits)} mono />
            <InfoRow label="Random Seed" value={String(ML_DEFAULTS.random_seed)} mono />
            <InfoRow label="Biological Target" value={ML_DEFAULTS.target} />
            <InfoRow label="Test Split" value={ML_DEFAULTS.test_split} />
            <InfoRow label="Validation Split" value={ML_DEFAULTS.validation_split} />
          </div>
          <p className="text-slate-600 text-xs mt-3">
            These values are hard-coded in ml_service.py and reflect the published training pipeline.
          </p>
        </SectionCard>

        {/* 5. Dataset Information */}
        <SectionCard icon={ICONS.database} title="Dataset Information" subtitle="EGFR / CHEMBL203 ChEMBL bioactivity datasets" accentColor="text-teal-400">
          <div>
            {[
              { name: 'EGFR_bioactivity_raw.csv', desc: 'Raw ChEMBL bioactivity export', available: true },
              { name: 'EGFR_ML_dataset.csv', desc: 'Preprocessed ML-ready dataset', available: true },
            ].map((ds) => (
              <div key={ds.name} className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
                <div>
                  <p className="text-slate-300 text-xs font-mono">{ds.name}</p>
                  <p className="text-slate-600 text-xs mt-0.5">{ds.desc}</p>
                </div>
                <span className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${ds.available ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${ds.available ? 'bg-emerald-400' : 'bg-red-400'}`} />
                  {ds.available ? 'Available' : 'Missing'}
                </span>
              </div>
            ))}
          </div>
          <p className="text-slate-600 text-xs mt-3">
            Source: ChEMBL v33 · Target: EGFR (ErbB1) · Organism: Homo sapiens
          </p>
        </SectionCard>

        {/* 6. System Status */}
        <SectionCard icon={ICONS.activity} title="System Status" subtitle="Live connectivity from GET /api/health" accentColor="text-green-400">
          {healthLoading ? (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3].map((i) => <div key={i} className="h-4 bg-surface-700 rounded w-full" />)}
            </div>
          ) : healthError ? (
            <Alert type="error" message="Unable to reach the backend. Check that the server is running." />
          ) : health ? (
            <div>
              <StatusDot ok={health.status === 'ok'} label="Backend API" />
              <StatusDot ok={health.database?.connected ?? false} label="Database" />
              <InfoRow label="API Version" value={health.version} mono />
              <InfoRow label="Database Type" value={health.database?.url_type ?? '—'} mono />
              <InfoRow label="Last Checked" value={new Date(health.timestamp).toLocaleTimeString()} />
            </div>
          ) : null}
          <div className="flex justify-end mt-3">
            <button
              id="settings-refresh-health"
              onClick={fetchHealth}
              disabled={healthLoading}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1.5"
            >
              <Icon path={ICONS.refresh} className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
        </SectionCard>

        {/* 7. Account */}
        <SectionCard icon={ICONS.logout} title="Account" subtitle="Session management" accentColor="text-orange-400">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white text-sm font-medium">Sign out</p>
              <p className="text-slate-500 text-xs mt-0.5">Clear your session and return to the login screen.</p>
            </div>
            <button
              id="settings-logout"
              onClick={handleLogout}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-orange-500/10 border border-orange-500/30 text-orange-400 hover:bg-orange-500/20 transition-all duration-150"
            >
              Sign Out
            </button>
          </div>
        </SectionCard>

        {/* 8. Danger Zone */}
        <SectionCard icon={ICONS.alert} title="Danger Zone" subtitle="Irreversible account actions" accentColor="text-red-400">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white text-sm font-medium">Delete Account</p>
              <p className="text-slate-500 text-xs mt-0.5">
                Permanent deletion is not available in this release. Contact your system administrator.
              </p>
            </div>
            <button
              id="settings-delete-account"
              disabled
              className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500/10 border border-red-500/20 text-red-500/50 cursor-not-allowed opacity-60"
            >
              Delete Account
            </button>
          </div>
        </SectionCard>

        {/* 9. Scientific Disclaimer */}
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4 flex gap-3">
          <Icon path={ICONS.info} className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-amber-400 text-xs font-semibold uppercase tracking-wider mb-1">
              Scientific Disclaimer
            </p>
            <p className="text-amber-200/60 text-xs leading-relaxed">
              All predictions generated by this platform are computational estimates for research purposes only.
              They do not constitute clinical advice, regulatory guidance, or guarantees of drug efficacy or
              safety. Results must be independently validated through appropriate experimental and regulatory
              processes before any clinical application.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default SettingsPage;
