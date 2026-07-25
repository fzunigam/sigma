import type { ReactNode } from 'react';

interface Props {
  title: string;
  hint?: string;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ title, hint, action, compact = false }: Props) {
  return (
    <div className={`text-center ${compact ? 'py-8 px-5' : 'py-14 px-6'}`}>
      <p className="text-[13px] font-medium text-text-muted">{title}</p>
      {hint && <p className="text-xs text-text-subtle mt-1 max-w-xs mx-auto">{hint}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
