import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Check } from 'lucide-react';

export interface Toast {
  id: number;
  tone: 'success' | 'error';
  text: string;
}

const DURATION_MS = 4000;

let nextId = 1;

/** Transient confirmations and failures. Errors that belong to a specific field
 *  are shown next to that field instead — a toast is for things that already
 *  happened somewhere else on the screen. */
export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback((tone: Toast['tone'], text: string) => {
    setToasts((current) => [...current, { id: nextId++, tone, text }]);
  }, []);

  return {
    toasts,
    dismiss,
    success: useCallback((text: string) => push('success', text), [push]),
    error: useCallback((text: string) => push('error', text), [push]),
  };
}

export function Toaster({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: number) => void;
}) {
  return (
    <div
      aria-live="polite"
      className="fixed bottom-5 right-5 z-60 flex flex-col items-end gap-2 pointer-events-none"
    >
      {toasts.map((toast) => (
        <ToastRow key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastRow({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), DURATION_MS);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const isError = toast.tone === 'error';

  return (
    <button
      type="button"
      onClick={() => onDismiss(toast.id)}
      className="pointer-events-auto flex items-center gap-2.5 max-w-sm text-left
        bg-surface border border-line-strong rounded-[var(--radius-control)]
        shadow-[var(--shadow-float)] pl-3 pr-4 py-2.5 animate-rise"
    >
      <span
        className={`grid place-items-center size-5 rounded-full shrink-0
          ${isError ? 'bg-negative/15 text-negative' : 'bg-positive/15 text-positive'}`}
      >
        {isError ? <AlertCircle size={12} /> : <Check size={12} />}
      </span>
      <span className="text-xs leading-snug">{toast.text}</span>
    </button>
  );
}
