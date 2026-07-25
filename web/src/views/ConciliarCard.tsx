import { useState } from 'react';
import { Check } from 'lucide-react';
import { Card, SectionHeader } from '../components/Card';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { Money } from '../components/Money';
import { api, ApiError } from '../lib/api';
import { money, shortDate } from '../lib/format';
import type { Summary } from '../lib/types';

interface Props {
  summary: Summary;
  onChanged: () => void;
  notify: { success: (text: string) => void; error: (text: string) => void };
}

/**
 * Conciliar closes every movement marked "incluir en la conciliación" into a
 * dated snapshot, and clears the mark. Past snapshots keep the link to the
 * movements they closed, so any of them can be opened again.
 */
export function ConciliarCard({ summary, onChanged, notify }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [running, setRunning] = useState(false);
  const { pending, reconciliations } = summary;

  async function reconcile() {
    setRunning(true);
    try {
      const result = await api.reconcile();
      notify.success(`Conciliación cerrada: ${money(result.net_amount)}.`);
      setConfirming(false);
      onChanged();
    } catch (caught) {
      notify.error(caught instanceof ApiError ? caught.message : 'No se pudo conciliar.');
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      <Card>
        <SectionHeader
          title="Pendiente de conciliar"
          hint={
            pending.count === 0
              ? 'Nada pendiente por ahora'
              : `${pending.count} ${pending.count === 1 ? 'movimiento' : 'movimientos'}`
          }
        />

        <Money
          amount={pending.net}
          tone="auto"
          signed={pending.net !== 0}
          className="block text-2xl font-semibold mt-3"
        />

        <Button
          variant="primary"
          full
          className="mt-4"
          disabled={pending.count === 0}
          icon={<Check size={14} />}
          onClick={() => setConfirming(true)}
        >
          Conciliar
        </Button>

        {reconciliations.length > 0 && (
          <div className="mt-5 pt-4 border-t border-line">
            <p className="text-[11px] font-medium text-text-subtle uppercase tracking-wide mb-2">
              Últimas conciliaciones
            </p>
            <ul className="space-y-1.5">
              {reconciliations.map((item) => (
                <li key={item.id} className="flex items-baseline justify-between gap-3">
                  <span className="text-xs text-text-muted">
                    {shortDate(item.date)}
                    <span className="text-text-subtle">
                      {' '}
                      · {item.movement_count || '—'}
                    </span>
                  </span>
                  <Money amount={item.net_amount} tone="auto" signed className="text-xs" />
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {confirming && (
        <Modal
          title="Conciliar movimientos"
          hint="Se guarda un resumen con la fecha de hoy y los movimientos dejan de estar pendientes."
          onClose={() => setConfirming(false)}
          footer={
            <>
              <Button onClick={() => setConfirming(false)}>Cancelar</Button>
              <Button variant="primary" loading={running} onClick={reconcile}>
                Conciliar
              </Button>
            </>
          }
        >
          <div className="rounded-[var(--radius-control)] bg-canvas border border-line p-4">
            <p className="text-xs text-text-muted">
              {pending.count} {pending.count === 1 ? 'movimiento' : 'movimientos'} · resultado
            </p>
            <Money
              amount={pending.net}
              tone="auto"
              signed
              className="block text-xl font-semibold mt-1"
            />
          </div>
          <p className="text-xs text-text-subtle mt-3">
            Puedes seguir editando o eliminando movimientos después; el resumen guarda lo que era
            cierto en este momento.
          </p>
        </Modal>
      )}
    </>
  );
}
