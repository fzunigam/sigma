import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}

export function Card({ children, className = '', padded = true }: CardProps) {
  return (
    <section
      className={`bg-surface border border-line rounded-[var(--radius-card)]
        shadow-[var(--shadow-card)] ${padded ? 'p-5' : ''} ${className}`}
    >
      {children}
    </section>
  );
}

interface SectionHeaderProps {
  title: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
}

export function SectionHeader({ title, hint, action, className = '' }: SectionHeaderProps) {
  return (
    <header className={`flex items-start justify-between gap-4 ${className}`}>
      <div className="min-w-0">
        <h2 className="text-[13px] font-semibold tracking-tight">{title}</h2>
        {hint && <p className="text-xs text-text-subtle mt-0.5">{hint}</p>}
      </div>
      {action}
    </header>
  );
}

interface PageHeaderProps {
  title: string;
  hint?: string;
  action?: ReactNode;
}

export function PageHeader({ title, hint, action }: PageHeaderProps) {
  return (
    <header className="flex items-end justify-between gap-4 mb-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {hint && <p className="text-sm text-text-muted mt-1">{hint}</p>}
      </div>
      {action}
    </header>
  );
}
