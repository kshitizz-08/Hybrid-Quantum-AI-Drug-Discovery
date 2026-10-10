import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/ui/Button';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register, isLoading, error, clearError } = useAuthStore();
  const [form, setForm] = useState({
    email: '',
    username: '',
    full_name: '',
    password: '',
    confirmPassword: '',
  });
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setValidationError(null);

    if (form.password !== form.confirmPassword) {
      setValidationError('Passwords do not match.');
      return;
    }
    if (form.password.length < 8) {
      setValidationError('Password must be at least 8 characters.');
      return;
    }
    if (!/^[a-zA-Z0-9_-]{3,50}$/.test(form.username.trim())) {
      setValidationError('Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens (no email or special characters).');
      return;
    }

    try {
      await register({
        email: form.email,
        username: form.username,
        password: form.password,
        full_name: form.full_name || undefined,
      });
      navigate('/dashboard');
    } catch {
      // Error is already in store
    }
  };

  const displayError = validationError || error;

  const passwordStrength = (() => {
    const p = form.password;
    if (!p) return null;
    let score = 0;
    if (p.length >= 8) score++;
    if (p.length >= 12) score++;
    if (/[A-Z]/.test(p)) score++;
    if (/[0-9]/.test(p)) score++;
    if (/[^A-Za-z0-9]/.test(p)) score++;
    if (score <= 1) return { label: 'Weak', color: 'bg-red-500', width: '20%' };
    if (score <= 2) return { label: 'Fair', color: 'bg-amber-500', width: '40%' };
    if (score <= 3) return { label: 'Good', color: 'bg-yellow-400', width: '60%' };
    if (score <= 4) return { label: 'Strong', color: 'bg-success-500', width: '80%' };
    return { label: 'Very Strong', color: 'bg-accent-500', width: '100%' };
  })();

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-20">
      <div className="absolute inset-0 dot-grid" />
      <div className="absolute inset-0 bg-hero-mesh" />

      <div className="relative z-10 w-full max-w-md animate-slide-up">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-500/30">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
              </svg>
            </div>
            <div className="text-left">
              <p className="text-sm font-bold text-white leading-none">QuantumDrug Platform</p>
              <p className="text-xs text-slate-500 leading-none mt-0.5">Drug Discovery Research</p>
            </div>
          </Link>
        </div>

        <div className="glass-card p-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-white mb-1">Create your account</h1>
            <p className="text-slate-400 text-sm">Join the drug discovery research platform</p>
          </div>

          {displayError && (
            <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex gap-2">
              <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {displayError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="full_name" className="block text-xs font-medium text-slate-400 mb-1.5">
                Full Name <span className="text-slate-600">(optional)</span>
              </label>
              <input
                id="full_name"
                type="text"
                autoComplete="name"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Dr. Jane Smith"
                className="form-input"
              />
            </div>

            <div>
              <label htmlFor="reg-email" className="block text-xs font-medium text-slate-400 mb-1.5">
                Email address
              </label>
              <input
                id="reg-email"
                type="email"
                autoComplete="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="researcher@university.edu"
                className="form-input"
              />
            </div>

            <div>
              <label htmlFor="username" className="block text-xs font-medium text-slate-400 mb-1.5">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                required
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="dr_smith_lab"
                className="form-input"
              />
              <p className="text-xs text-slate-600 mt-1">Letters, numbers, _ and - only.</p>
            </div>

            <div>
              <label htmlFor="reg-password" className="block text-xs font-medium text-slate-400 mb-1.5">
                Password
              </label>
              <input
                id="reg-password"
                type="password"
                autoComplete="new-password"
                required
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Minimum 8 characters"
                className="form-input"
              />
              {passwordStrength && (
                <div className="mt-2">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-slate-600">Password strength</span>
                    <span className={`text-xs font-medium ${
                      passwordStrength.label === 'Weak' ? 'text-red-400' :
                      passwordStrength.label === 'Fair' ? 'text-amber-400' :
                      passwordStrength.label === 'Good' ? 'text-yellow-400' :
                      'text-success-400'
                    }`}>{passwordStrength.label}</span>
                  </div>
                  <div className="h-1 bg-surface-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${passwordStrength.color}`}
                      style={{ width: passwordStrength.width }}
                    />
                  </div>
                </div>
              )}
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-xs font-medium text-slate-400 mb-1.5">
                Confirm Password
              </label>
              <input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={form.confirmPassword}
                onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                placeholder="••••••••"
                className={`form-input ${
                  form.confirmPassword && form.confirmPassword !== form.password
                    ? 'border-red-500/50 focus:border-red-500/50'
                    : ''
                }`}
              />
            </div>

            <Button type="submit" fullWidth loading={isLoading} className="mt-2">
              Create Research Account
            </Button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center text-xs text-slate-600 mt-4 max-w-sm mx-auto">
          Computational research platform only. Results do not constitute clinical or medical advice.
        </p>
      </div>
    </div>
  );
};
