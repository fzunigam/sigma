import { useEffect, useState } from 'react';
import { ArrowDownToLine } from 'lucide-react';
import { api } from '../lib/api';
import { openReleases } from '../lib/bridge';
import type { UpdateStatus } from '../lib/types';

/**
 * A line in the sidebar footer when a newer version has been published, and
 * nothing at all otherwise. Offline the check simply fails and nothing shows:
 * the app never depends on the network to work.
 */
export function UpdateNotice() {
  const [update, setUpdate] = useState<UpdateStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .updateStatus()
      .then((status) => {
        if (!cancelled) setUpdate(status);
      })
      .catch(() => {
        // No connection, or GitHub did not answer. Nobody needs to hear about
        // it: stay quiet until Sigma is opened again.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!update?.available) return null;

  return (
    <button
      type="button"
      onClick={() => void openReleases(update.url)}
      title="Abrir la página de descargas"
      className="flex items-center gap-1.5 w-full px-1.5 pb-2 text-[11px]
        text-accent hover:underline transition-colors duration-150"
    >
      <ArrowDownToLine size={12} className="shrink-0" />
      <span className="truncate">Versión {update.latest} disponible</span>
    </button>
  );
}
