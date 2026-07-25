import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-accent text-accent-contrast hover:brightness-110 active:brightness-95 font-semibold',
  secondary: 'bg-surface-hover text-text border border-line hover:border-line-strong',
  ghost: 'text-text-muted hover:text-text hover:bg-surface-hover',
  danger: 'text-negative border border-negative/25 hover:bg-negative/10',
};

const SIZES: Record<Size, string> = {
  sm: 'h-7 px-2.5 text-xs gap-1.5 rounded-[6px]',
  md: 'h-9 px-3.5 text-sm gap-2 rounded-[var(--radius-control)]',
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  full?: boolean;
}

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  icon,
  full = false,
  disabled,
  children,
  className = '',
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center whitespace-nowrap transition-all duration-150
        disabled:opacity-40 disabled:pointer-events-none
        ${VARIANTS[variant]} ${SIZES[size]} ${full ? 'w-full' : ''} ${className}`}
    >
      {loading ? <Loader2 size={size === 'sm' ? 12 : 14} className="animate-spin" /> : icon}
      {children}
    </button>
  );
}
