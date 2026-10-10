import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';

// ── Pipeline steps data ────────────────────────────────────────
const pipelineSteps = [
  { icon: '🔬', label: 'Data Collection', desc: 'ChEMBL bioactivity records', color: 'from-violet-500 to-purple-600' },
  { icon: '⚗️', label: 'Preprocessing', desc: 'Filtering & pIC50 calculation', color: 'from-blue-500 to-indigo-600' },
  { icon: '🧬', label: 'Feature Extraction', desc: 'RDKit molecular descriptors', color: 'from-cyan-500 to-blue-600' },
  { icon: '🤖', label: 'AI Prediction', desc: 'Random Forest & XGBoost', color: 'from-teal-500 to-cyan-600' },
  { icon: '🔍', label: 'Candidate Filtering', desc: 'Drug-likeness screening', color: 'from-green-500 to-teal-600' },
  { icon: '⚛️', label: 'Quantum Optimization', desc: 'QAOA candidate selection', color: 'from-amber-500 to-orange-600' },
  { icon: '🏗️', label: 'Molecular Docking', desc: 'AutoDock Vina binding', color: 'from-orange-500 to-red-600' },
  { icon: '🏆', label: 'Final Ranking', desc: 'Composite scoring', color: 'from-rose-500 to-pink-600' },
];

const techStack = [
  { category: 'Frontend', items: ['React', 'Vite', 'TypeScript', 'Tailwind CSS', '3Dmol.js'] },
  { category: 'Backend', items: ['FastAPI', 'PostgreSQL', 'SQLAlchemy', 'Redis', 'Celery'] },
  { category: 'AI / ML', items: ['scikit-learn', 'XGBoost', 'RDKit', 'Pandas', 'NumPy'] },
  { category: 'Quantum', items: ['Qiskit', 'QAOA', 'QUBO', 'Qiskit Optimization'] },
  { category: 'Docking', items: ['AutoDock Vina', 'Meeko', 'RDKit 3D', 'PDB'] },
  { category: 'DevOps', items: ['Docker', 'docker-compose', 'Python 3.13', 'Node 22'] },
];

// ── Animated molecule SVG ──────────────────────────────────────
const MoleculeGraphic: React.FC = () => (
  <svg viewBox="0 0 300 300" className="w-full h-full opacity-20" fill="none">
    {/* Bonds */}
    <line x1="150" y1="150" x2="90" y2="90"   stroke="#6366f1" strokeWidth="2" opacity="0.6" />
    <line x1="150" y1="150" x2="210" y2="90"   stroke="#06b6d4" strokeWidth="2" opacity="0.6" />
    <line x1="150" y1="150" x2="90" y2="210"   stroke="#6366f1" strokeWidth="2" opacity="0.6" />
    <line x1="150" y1="150" x2="210" y2="210"  stroke="#06b6d4" strokeWidth="2" opacity="0.6" />
    <line x1="90"  y1="90"  x2="50"  y2="120"  stroke="#818cf8" strokeWidth="1.5" opacity="0.4" />
    <line x1="210" y1="90"  x2="250" y2="120"  stroke="#22d3ee" strokeWidth="1.5" opacity="0.4" />
    <line x1="90"  y1="210" x2="50"  y2="180"  stroke="#818cf8" strokeWidth="1.5" opacity="0.4" />
    <line x1="210" y1="210" x2="250" y2="180"  stroke="#22d3ee" strokeWidth="1.5" opacity="0.4" />
    {/* Atoms */}
    <circle cx="150" cy="150" r="14" fill="#4f46e5" opacity="0.9" />
    <circle cx="90"  cy="90"  r="10" fill="#6366f1" opacity="0.8" />
    <circle cx="210" cy="90"  r="10" fill="#0891b2" opacity="0.8" />
    <circle cx="90"  cy="210" r="10" fill="#6366f1" opacity="0.8" />
    <circle cx="210" cy="210" r="10" fill="#0891b2" opacity="0.8" />
    <circle cx="50"  cy="120" r="7"  fill="#818cf8" opacity="0.6" />
    <circle cx="250" cy="120" r="7"  fill="#22d3ee" opacity="0.6" />
    <circle cx="50"  cy="180" r="7"  fill="#818cf8" opacity="0.6" />
    <circle cx="250" cy="180" r="7"  fill="#22d3ee" opacity="0.6" />
    {/* Orbit ring */}
    <circle cx="150" cy="150" r="70" stroke="#6366f1" strokeWidth="1" strokeDasharray="4 6" opacity="0.3" />
    <circle cx="150" cy="150" r="110" stroke="#06b6d4" strokeWidth="0.5" strokeDasharray="3 8" opacity="0.2" />
  </svg>
);

export const LandingPage: React.FC = () => {
  const heroRef = useRef<HTMLDivElement>(null);

  // Parallax scroll effect on hero
  useEffect(() => {
    const handleScroll = () => {
      if (heroRef.current) {
        const scrolled = window.scrollY;
        heroRef.current.style.transform = `translateY(${scrolled * 0.3}px)`;
        heroRef.current.style.opacity = `${1 - scrolled / 600}`;
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen">

      {/* ── HERO ─────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
        {/* Background effects */}
        <div className="absolute inset-0 dot-grid" />
        <div className="absolute inset-0 bg-hero-mesh" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-accent-600/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1.5s' }} />

        <div ref={heroRef} className="relative z-10 max-w-6xl mx-auto px-4 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 glass-card px-4 py-2 mb-8 animate-slide-up">
            <span className="w-2 h-2 rounded-full bg-success-400 animate-pulse" />
            <span className="text-sm text-slate-300 font-medium">Final Year Engineering Project · EGFR Drug Discovery</span>
          </div>

          {/* Title */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black leading-[1.05] mb-6 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <span className="text-white">Hybrid</span>{' '}
            <span className="gradient-text">Quantum-AI</span>
            <br />
            <span className="text-white">Drug Discovery</span>
            <br />
            <span className="text-slate-400 text-4xl sm:text-5xl lg:text-6xl font-light">Platform</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up" style={{ animationDelay: '0.2s' }}>
            AI-driven molecular analysis, quantum optimization, and molecular docking for
            <strong className="text-slate-300"> computational drug candidate prioritization.</strong>
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <Link to="/register">
              <Button size="lg" className="glow-primary">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Start Discovering
              </Button>
            </Link>
            <a href="#how-it-works">
              <Button variant="secondary" size="lg">
                Explore the Pipeline
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Button>
            </a>
          </div>

          {/* Molecule graphic */}
          <div className="absolute right-0 top-1/2 -translate-y-1/2 w-64 h-64 pointer-events-none hidden xl:block animate-spin-slow">
            <MoleculeGraphic />
          </div>
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-48 h-48 pointer-events-none hidden xl:block animate-spin-slow" style={{ animationDirection: 'reverse' }}>
            <MoleculeGraphic />
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center pt-2">
            <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-ping" />
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <div className="section-divider mx-auto mb-4" />
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">How It Works</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              A complete end-to-end computational pipeline from raw bioactivity data to
              ranked drug candidates — reproducible, transparent, and explainable.
            </p>
          </div>

          {/* Pipeline */}
          <div className="relative">
            {/* Connector line */}
            <div className="absolute left-1/2 top-8 bottom-8 w-px bg-gradient-to-b from-primary-500/60 via-accent-500/40 to-transparent hidden lg:block" />

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
              {pipelineSteps.map((step, i) => (
                <div key={step.label} className="glass-card-hover p-5 text-center relative">
                  <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${step.color} text-2xl mb-3 shadow-lg`}>
                    {step.icon}
                  </div>
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-surface-800 border border-white/10 flex items-center justify-center">
                    <span className="text-[9px] font-bold text-slate-400">{i + 1}</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm mb-1">{step.label}</h3>
                  <p className="text-slate-500 text-xs">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── AI ANALYSIS ──────────────────────────────────────── */}
      <section id="pipeline" className="py-24 px-4 bg-surface-800/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="section-divider mb-4" />
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">AI-Based Bioactivity Prediction</h2>
              <p className="text-slate-400 mb-6 leading-relaxed">
                Machine learning models trained on real ChEMBL bioactivity data predict
                pIC50 values for each screened compound. All reported metrics come from
                actual model training — no results are fabricated.
              </p>
              <ul className="space-y-3">
                {[
                  { label: 'Random Forest', desc: 'Ensemble of decision trees on Morgan fingerprints + descriptors' },
                  { label: 'XGBoost', desc: 'Gradient boosting with cross-validated hyperparameter search' },
                  { label: 'Real Metrics', desc: 'MAE, RMSE, R² — computed from held-out test set only' },
                  { label: 'No Data Leakage', desc: 'Stratified train/val/test split with fingerprint sanitization' },
                ].map((item) => (
                  <li key={item.label} className="flex gap-3">
                    <div className="w-5 h-5 rounded-full bg-primary-500/20 flex items-center justify-center shrink-0 mt-0.5">
                      <svg className="w-3 h-3 text-primary-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div>
                      <span className="text-white text-sm font-medium">{item.label}</span>
                      <span className="text-slate-500 text-sm"> — {item.desc}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Feature panel */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="ml-2 text-xs text-slate-500 font-mono">feature_importance.py</span>
              </div>
              <div className="font-mono text-xs space-y-1">
                <p><span className="text-accent-400">model</span> <span className="text-slate-500">=</span> <span className="text-primary-300">XGBRegressor</span><span className="text-slate-500">(</span></p>
                <p className="pl-4"><span className="text-amber-300">n_estimators</span><span className="text-slate-500">=</span><span className="text-green-400">500</span><span className="text-slate-500">,</span></p>
                <p className="pl-4"><span className="text-amber-300">max_depth</span><span className="text-slate-500">=</span><span className="text-green-400">6</span><span className="text-slate-500">,</span></p>
                <p className="pl-4"><span className="text-amber-300">learning_rate</span><span className="text-slate-500">=</span><span className="text-green-400">0.05</span></p>
                <p><span className="text-slate-500">)</span></p>
                <p className="mt-2"><span className="text-slate-600"># Results from actual training:</span></p>
                <p><span className="text-accent-400">metrics</span> <span className="text-slate-500">=</span> <span className="text-slate-500">{"{"}</span></p>
                <p className="pl-4"><span className="text-amber-300">"mae"</span><span className="text-slate-500">:</span> <span className="text-slate-400">computed_from_test_set</span><span className="text-slate-500">,</span></p>
                <p className="pl-4"><span className="text-amber-300">"rmse"</span><span className="text-slate-500">:</span> <span className="text-slate-400">computed_from_test_set</span><span className="text-slate-500">,</span></p>
                <p className="pl-4"><span className="text-amber-300">"r2"</span><span className="text-slate-500">:</span> <span className="text-slate-400">computed_from_test_set</span></p>
                <p><span className="text-slate-500">{"}"}</span></p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── QUANTUM OPTIMIZATION ─────────────────────────────── */}
      <section className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Quantum circuit visual */}
            <div className="glass-card p-6 order-2 lg:order-1">
              <p className="text-xs text-slate-500 font-mono mb-4">QAOA — Quantum Approximate Optimization</p>
              <div className="space-y-2">
                {['q[0]', 'q[1]', 'q[2]', 'q[3]'].map((q, i) => (
                  <div key={q} className="flex items-center gap-2">
                    <span className="text-xs font-mono text-accent-400 w-8">{q}</span>
                    <div className="flex-1 h-px bg-white/10 relative">
                      <div
                        className="absolute top-1/2 -translate-y-1/2 w-6 h-6 rounded border border-primary-500/60 bg-primary-500/10 flex items-center justify-center"
                        style={{ left: `${10 + i * 8}%` }}
                      >
                        <span className="text-[8px] text-primary-400">H</span>
                      </div>
                      <div
                        className="absolute top-1/2 -translate-y-1/2 w-6 h-6 rounded border border-accent-500/60 bg-accent-500/10 flex items-center justify-center"
                        style={{ left: `${40 + i * 5}%` }}
                      >
                        <span className="text-[8px] text-accent-400">Rz</span>
                      </div>
                      <div
                        className="absolute top-1/2 -translate-y-1/2 w-6 h-6 rounded border border-amber-500/60 bg-amber-500/10 flex items-center justify-center"
                        style={{ left: `${70 + i * 3}%` }}
                      >
                        <span className="text-[8px] text-amber-400">M</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="bg-surface-700/50 rounded-lg p-3 text-center">
                  <p className="text-xs text-slate-500">Backend</p>
                  <p className="text-sm font-semibold text-accent-300">Qiskit Simulator</p>
                </div>
                <div className="bg-surface-700/50 rounded-lg p-3 text-center">
                  <p className="text-xs text-slate-500">Comparison</p>
                  <p className="text-sm font-semibold text-primary-300">Classical Baseline</p>
                </div>
              </div>
            </div>

            <div className="order-1 lg:order-2">
              <div className="section-divider mb-4" />
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Quantum Candidate Optimization</h2>
              <p className="text-slate-400 mb-6 leading-relaxed">
                Top AI-ranked candidates are encoded into a QUBO problem and optimized
                using QAOA via Qiskit. A classical solver runs in parallel for fair comparison.
              </p>
              <div className="glass-card p-4 border border-amber-500/20">
                <div className="flex gap-2 items-start">
                  <span className="text-amber-400 text-lg">⚠️</span>
                  <p className="text-sm text-slate-400">
                    <strong className="text-amber-300">No false quantum advantage claims.</strong>{' '}
                    Results show both classical and QAOA solutions. Runtime and objective values
                    are measured from actual computation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── TECHNOLOGY STACK ─────────────────────────────────── */}
      <section id="technology" className="py-24 px-4 bg-surface-800/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <div className="section-divider mx-auto mb-4" />
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Technology Stack</h2>
            <p className="text-slate-400">Production-grade open-source tools across the full stack</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 stagger-children">
            {techStack.map((tech) => (
              <div key={tech.category} className="glass-card-hover p-5">
                <h3 className="font-semibold text-white mb-3 text-sm">{tech.category}</h3>
                <div className="flex flex-wrap gap-2">
                  {tech.items.map((item) => (
                    <span key={item} className="text-xs bg-surface-700 text-slate-400 px-2.5 py-1 rounded-lg border border-white/5">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DISCLAIMER ───────────────────────────────────────── */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="glass-card p-6 border border-amber-500/20 text-center">
            <div className="w-10 h-10 rounded-xl bg-amber-500/15 flex items-center justify-center mx-auto mb-4">
              <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="font-semibold text-white mb-2">Scientific Disclaimer</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Results generated by this platform are <strong className="text-white">computational predictions
              and prioritization results</strong>. They do not constitute clinical validation, medical advice,
              or proof of drug efficacy or safety. This is a research and educational tool for
              computational drug discovery exploration.
            </p>
          </div>
        </div>
      </section>

      {/* ── CTA FOOTER ───────────────────────────────────────── */}
      <section className="py-24 px-4 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Ready to explore{' '}
            <span className="gradient-text">EGFR candidates?</span>
          </h2>
          <p className="text-slate-400 mb-8">
            Create an account to start a drug discovery experiment, run the full pipeline,
            and explore computationally predicted candidates.
          </p>
          <Link to="/register">
            <Button size="lg" className="glow-primary">
              Create Free Account
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 px-4 text-center">
        <p className="text-slate-600 text-sm">
          Hybrid Quantum-AI Drug Discovery Platform · Final Year Engineering Project · {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
};
