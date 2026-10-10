import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { NewDiscoveryPage } from './pages/NewDiscoveryPage';
import { ExperimentDetailPage } from './pages/ExperimentDetailPage';
import { AIResultsPage } from './pages/AIResultsPage';
import { ADMETPage } from './pages/ADMETPage';
import { QuantumPage } from './pages/QuantumPage';
import DockingPage from './pages/DockingPage';
import RankingPage from './pages/RankingPage';
import { SettingsPage } from './pages/SettingsPage';
import { ModelManagementPage } from './pages/ModelManagementPage';
import { useAuthStore } from './store/authStore';

// ── Route-aware layout wrapper ──────────────────────────────────────
const AppLayout: React.FC = () => {
  const { isAuthenticated, fetchMe } = useAuthStore();
  const location = useLocation();
  const isPublicPage = ['/', '/login', '/register'].includes(location.pathname);

  // Re-validate JWT on mount (runs once)
  useEffect(() => {
    if (isAuthenticated) {
      fetchMe().catch(() => {
        // If /me fails (e.g. token expired), the 401 interceptor handles logout
      });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-surface-900">
      <Navbar />
      {/* Sidebar only on authenticated interior pages */}
      {isAuthenticated && !isPublicPage && <Sidebar />}
      <main>
        <Routes>
          {/* ── Public routes ────────────────────────────────────────── */}
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/login"
            element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />}
          />
          <Route
            path="/register"
            element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />}
          />

          {/* ── Protected routes ─────────────────────────────────────── */}
          <Route
            path="/dashboard"
            element={isAuthenticated ? <DashboardPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/experiments"
            element={isAuthenticated ? <ExperimentsPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/experiments/:id"
            element={isAuthenticated ? <ExperimentDetailPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/experiments/:id/ai"
            element={isAuthenticated ? <AIResultsPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/experiments/:id/admet"
            element={isAuthenticated ? <ADMETPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/experiments/:id/quantum"
            element={isAuthenticated ? <QuantumPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/experiments/:experimentId/docking"
            element={isAuthenticated ? <DockingPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/experiments/:experimentId/ranking"
            element={isAuthenticated ? <RankingPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/new-discovery"
            element={isAuthenticated ? <NewDiscoveryPage /> : <Navigate to="/login" replace />}
          />

          {/* ── Model Registry & Settings ────────────────────────────── */}
          <Route
            path="/models"
            element={isAuthenticated ? <ModelManagementPage /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/settings"
            element={isAuthenticated ? <SettingsPage /> : <Navigate to="/login" replace />}
          />

          {/* ── 404 ──────────────────────────────────────────────────── */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
};

const NotFound: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <p className="text-8xl font-black gradient-text mb-4">404</p>
      <h1 className="text-2xl font-bold text-white mb-2">Page Not Found</h1>
      <p className="text-slate-400 mb-6">The page you're looking for doesn't exist.</p>
      <a href="/" className="text-primary-400 hover:text-primary-300 transition-colors text-sm">
        ← Back to home
      </a>
    </div>
  </div>
);

// ── Root App ────────────────────────────────────────────────────────
const App: React.FC = () => (
  <BrowserRouter>
    <AppLayout />
  </BrowserRouter>
);

export default App;
