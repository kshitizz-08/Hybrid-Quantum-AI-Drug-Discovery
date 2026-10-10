import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Button } from '../ui/Button';

export const Navbar: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const isLanding = location.pathname === '/';

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50">
      {/* Glass navbar */}
      <div className={`border-b transition-all duration-300 ${
        isLanding
          ? 'bg-surface-900/60 border-white/5 backdrop-blur-md'
          : 'bg-surface-800/80 border-white/5 backdrop-blur-md'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="relative">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-500/30">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
                  </svg>
                </div>
                <div className="absolute -inset-1 rounded-lg bg-gradient-to-br from-primary-500/20 to-accent-500/20 blur opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-bold text-white leading-none">QuantumDrug</p>
                <p className="text-[10px] text-slate-500 leading-none mt-0.5">Discovery Platform</p>
              </div>
            </Link>

            {/* Navigation */}
            {isAuthenticated ? (
              <nav className="hidden md:flex items-center gap-1">
                <NavItem to="/dashboard" label="Dashboard" />
                <NavItem to="/experiments" label="Experiments" />
                <NavItem to="/models" label="Models" />
              </nav>
            ) : (
              <nav className="hidden md:flex items-center gap-6">
                <a href="#how-it-works" className="text-slate-400 hover:text-white text-sm transition-colors">How It Works</a>
                <a href="#technology" className="text-slate-400 hover:text-white text-sm transition-colors">Technology</a>
                <a href="#pipeline" className="text-slate-400 hover:text-white text-sm transition-colors">Pipeline</a>
              </nav>
            )}

            {/* Right actions */}
            <div className="flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  {/* User pill */}
                  <div className="hidden md:flex items-center gap-2 glass-card px-3 py-1.5">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-xs font-bold text-white">
                      {user?.username?.[0]?.toUpperCase() ?? 'U'}
                    </div>
                    <span className="text-sm text-slate-300">{user?.username}</span>
                  </div>
                  <Button variant="ghost" size="sm" onClick={handleLogout}>
                    Logout
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => navigate('/new-discovery')}
                    icon={
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    }
                  >
                    New Discovery
                  </Button>
                </>
              ) : (
                <>
                  <Link to="/login">
                    <Button variant="ghost" size="sm">Sign In</Button>
                  </Link>
                  <Link to="/register">
                    <Button size="sm">Get Started</Button>
                  </Link>
                </>
              )}

              {/* Mobile menu toggle */}
              <button
                className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-surface-700 transition-colors"
                onClick={() => setMenuOpen(!menuOpen)}
                aria-label="Toggle menu"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {menuOpen
                    ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
                </svg>
              </button>
            </div>
          </div>

          {/* Mobile menu */}
          {menuOpen && (
            <div className="md:hidden py-3 border-t border-white/5 space-y-1 animate-fade-in">
              {isAuthenticated ? (
                <>
                  <MobileNavItem to="/dashboard" label="Dashboard" onClick={() => setMenuOpen(false)} />
                  <MobileNavItem to="/experiments" label="Experiments" onClick={() => setMenuOpen(false)} />
                  <MobileNavItem to="/models" label="Models" onClick={() => setMenuOpen(false)} />
                  <button onClick={handleLogout} className="block w-full text-left px-3 py-2 text-slate-400 text-sm hover:text-white">
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <MobileNavItem to="/login" label="Sign In" onClick={() => setMenuOpen(false)} />
                  <MobileNavItem to="/register" label="Get Started" onClick={() => setMenuOpen(false)} />
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

// ── Sub-components ──────────────────────────────────────────

const NavItem: React.FC<{ to: string; label: string }> = ({ to, label }) => {
  const { pathname } = useLocation();
  const active = pathname.startsWith(to);
  return (
    <Link
      to={to}
      className={`nav-link ${active ? 'active' : ''}`}
    >
      {label}
    </Link>
  );
};

const MobileNavItem: React.FC<{ to: string; label: string; onClick: () => void }> = ({ to, label, onClick }) => (
  <Link
    to={to}
    onClick={onClick}
    className="block px-3 py-2 text-slate-300 hover:text-white text-sm rounded-lg hover:bg-surface-700 transition-colors"
  >
    {label}
  </Link>
);
