import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  glow?: 'primary' | 'accent' | 'none';
}

const paddingClasses = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

const glowClasses = {
  none: '',
  primary: 'glow-primary',
  accent: 'glow-accent',
};

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  hover = false,
  padding = 'md',
  glow = 'none',
}) => {
  return (
    <div
      className={[
        hover ? 'glass-card-hover' : 'glass-card',
        paddingClasses[padding],
        glowClasses[glow],
        className,
      ].join(' ')}
    >
      {children}
    </div>
  );
};

// ── Stat Card ─────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: { value: number; label: string };
  color?: 'primary' | 'accent' | 'success' | 'warning';
  className?: string;
}

const colorMap = {
  primary: {
    icon: 'bg-primary-500/15 text-primary-400',
    value: 'text-primary-300',
  },
  accent: {
    icon: 'bg-accent-500/15 text-accent-400',
    value: 'text-accent-300',
  },
  success: {
    icon: 'bg-success-500/15 text-success-400',
    value: 'text-success-300',
  },
  warning: {
    icon: 'bg-warning-500/15 text-warning-400',
    value: 'text-warning-300',
  },
};

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon,
  color = 'primary',
  className = '',
}) => {
  const colors = colorMap[color];
  return (
    <Card hover className={className}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">{label}</p>
          <p className={`text-3xl font-bold ${colors.value}`}>{value}</p>
        </div>
        <div className={`p-3 rounded-xl ${colors.icon}`}>
          {icon}
        </div>
      </div>
    </Card>
  );
};
