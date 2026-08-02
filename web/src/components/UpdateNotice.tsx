import { useEffect, useState } from 'react';
import { ArrowDownToLine, TriangleAlert } from 'lucide-react';
import { Button } from './Button';
import { Modal } from './Modal';
import { api, ApiError } from '../lib/api';
import * as bridge from '../lib/bridge';
import type { UpdateStatus } from '../lib/types';

/**
 * A line in the sidebar footer when a newer version has been published, and
 * nothing at all otherwise. Offline the check simply fails and nothing shows:
 * the app never depends on the network to work.
 */
export function UpdateNotice() {
  const [update, setUpdate] = useState<UpdateStatus | null>(null);
  const [asking, setAsking] = useState(false);

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
    <>
      <button
        type="button"
        onClick={() => setAsking(true)}
        className="flex items-center gap-1.5 w-full px-1.5 pb-2 text-[11px]
          text-accent hover:underline transition-colors duration-150"
      >
        <ArrowDownToLine size={12} className="shrink-0" />
        <span className="truncate">Versión {update.latest} disponible</span>
      </button>

      {asking && <ActualizarModal update={update} onClose={() => setAsking(false)} />}
    </>
  );
}

function ActualizarModal({ update, onClose }: { update: UpdateStatus; onClose: () => void }) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function install() {
    setWorking(true);
    setError(null);
    try {
      await api.installUpdate();
      // Everything is in place and the swap is waiting for this window to
      // close, so from here on there is nothing left to cancel.
      await bridge.quit();
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'No se pudo instalar la versión nueva.',
      );
      setWorking(false);
    }
  }

  return (
    <Modal
      title="Actualizar Sigma"
      hint={`Tienes la versión ${update.current}. La última es la ${update.latest}.`}
      onClose={working ? () => undefined : onClose}
      footer={
        <>
          <Button onClick={onClose} disabled={working}>
            Ahora no
          </Button>
          <Button variant="primary" loading={working} onClick={install}>
            {working ? 'Instalando…' : 'Actualizar'}
          </Button>
        </>
      }
    >
      <p className="text-xs text-text-muted leading-relaxed">
        Sigma descargará la versión {update.latest}, la instalará y se abrirá de nuevo sola.
        Demora un par de minutos y no hay que hacer nada más.
      </p>
      <p className="text-xs text-text-muted leading-relaxed mt-3">
        Tus datos y tus ajustes no se tocan: viven en tu archivo, fuera de la aplicación.
      </p>

      {error && (
        <div
          className="flex items-start gap-2 mt-4 p-3 rounded-[var(--radius-control)]
            border border-caution/30 bg-caution/10"
        >
          <TriangleAlert size={13} className="text-caution mt-px shrink-0" />
          <p className="text-xs leading-relaxed">
            {error}{' '}
            <button
              type="button"
              onClick={() => void bridge.openReleases(update.url)}
              className="text-accent hover:underline"
            >
              Abrir la página de descargas
            </button>
          </p>
        </div>
      )}
    </Modal>
  );
}
