import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  title: string;
  hint?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: 'sm' | 'md';
}

export function Modal({ title, hint, onClose, children, footer, width = 'sm' }: Props) {
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    // Move focus into the dialog so Tab stays inside it and Escape works at once.
    panel.current?.querySelector<HTMLElement>('input, select, button')?.focus();
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6
        bg-black/50 backdrop-blur-[3px] animate-fade"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`w-full ${width === 'sm' ? 'max-w-sm' : 'max-w-lg'} bg-surface
          border border-line-strong rounded-[var(--radius-card)]
          shadow-[var(--shadow-float)] animate-pop`}
      >
        <header className="flex items-start justify-between gap-4 p-5 pb-0">
          <div>
            <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
            {hint && <p className="text-xs text-text-subtle mt-1">{hint}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="text-text-subtle hover:text-text transition-colors -mt-1 -mr-1 p-1"
          >
            <X size={15} />
          </button>
        </header>

        <div className="p-5">{children}</div>

        {footer && (
          <footer className="flex justify-end gap-2 px-5 py-4 border-t border-line">
            {footer}
          </footer>
        )}
      </div>
    </div>
  );
}
