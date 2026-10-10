import React from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  fullWidth?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary: [
    'bg-gradient-to-r from-primary-600 to-primary-500',
    'hover:from-primary-500 hover:to-primary-400',
    'text-white shadow-lg shadow-primary-500/25',
    'border border-primary-400/30',
  ].join(' '),
  secondary: [
    'bg-surface-700 hover:bg-surface-600',
    'text-white border border-white/10 hover:border-white/20',
  ].join(' '),
  ghost: [
    'bg-transparent hover:bg-surface-700',
    'text-slate-300 hover:text-white',
    'border border-transparent hover:border-white/10',
  ].join(' '),
  danger: [
    'bg-red-600/80 hover:bg-red-500',
    'text-white border border-red-500/30',
    'shadow-lg shadow-red-500/20',
  ].join(' '),
  success: [
    'bg-success-600/80 hover:bg-success-500',
    'text-white border border-success-500/30',
    'shadow-lg shadow-success-500/20',
  ].join(' '),
};

const sizeClasses: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-5 py-2.5 text-sm gap-2',
  lg: 'px-7 py-3.5 text-base gap-2.5',
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconRight,
  fullWidth = false,
  children,
  disabled,
  className = '',
  ...props
}) => {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={[
        'inline-flex items-center justify-center font-medium rounded-xl',
        'transition-all duration-200 active:scale-[0.97]',
        'focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:ring-offset-1 focus:ring-offset-surface-900',
        variantClasses[variant],
        sizeClasses[size],
        fullWidth ? 'w-full' : '',
        isDisabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : 'cursor-pointer',
        className,
      ].join(' ')}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children}
      {iconRight && !loading && <span className="shrink-0">{iconRight}</span>}
    </button>
  );
};
