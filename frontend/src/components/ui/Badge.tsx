import React from 'react';
import { JobStatus, ExperimentStatus } from '../../types';

type BadgeVariant = 'primary' | 'accent' | 'success' | 'warning' | 'danger' | 'ghost';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  primary: 'bg-primary-500/15 text-primary-300 border-primary-500/20',
  accent:  'bg-accent-500/15  text-accent-300  border-accent-500/20',
  success: 'bg-success-500/15 text-success-400 border-success-500/20',
  warning: 'bg-warning-500/15 text-warning-400 border-warning-500/20',
  danger:  'bg-red-500/15     text-red-400     border-red-500/20',
  ghost:   'bg-surface-700    text-slate-400   border-white/5',
};

const dotColors: Record<BadgeVariant, string> = {
  primary: 'bg-primary-400',
  accent:  'bg-accent-400',
  success: 'bg-success-400',
  warning: 'bg-warning-400',
  danger:  'bg-red-400',
  ghost:   'bg-slate-500',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'ghost',
  size = 'sm',
  dot = false,
  className = '',
}) => {
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        variantClasses[variant],
        className,
      ].join(' ')}
    >
      {dot && (
        <span
          className={[
            'w-1.5 h-1.5 rounded-full shrink-0',
            dotColors[variant],
            variant === 'warning' ? 'animate-pulse' : '',
          ].join(' ')}
        />
      )}
      {children}
    </span>
  );
};

// ── Status Badge helpers ───────────────────────────────────────

const statusConfig: Record<JobStatus | ExperimentStatus, { label: string; variant: BadgeVariant; dot: boolean }> = {
  PENDING:   { label: 'Pending',   variant: 'ghost',   dot: false },
  RUNNING:   { label: 'Running',   variant: 'warning', dot: true  },
  COMPLETED: { label: 'Completed', variant: 'success', dot: false },
  FAILED:    { label: 'Failed',    variant: 'danger',  dot: false },
};

export const StatusBadge: React.FC<{ status: JobStatus | ExperimentStatus }> = ({ status }) => {
  const config = statusConfig[status] || statusConfig.PENDING;
  return (
    <Badge variant={config.variant} dot={config.dot}>
      {config.label}
    </Badge>
  );
};
