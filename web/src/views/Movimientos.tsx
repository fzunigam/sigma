import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, PageHeader } from '../components/Card';
import { ActivityList } from '../components/ActivityList';
import { Money } from '../components/Money';
import { api, ApiError } from '../lib/api';
import { currentPeriod, monthLabel } from '../lib/format';
import type { Activity } from '../lib/types';

interface Props {
  onDelete: (item: Activity) => void;
  reloadToken: number;
  notify: { error: (text: string) => void };
}

/** One month at a time, moved with the arrows. No filter form to fill in. */
export function Movimientos({ onDelete, reloadToken, notify }: Props) {
  const [period, setPeriod] = useState(currentPeriod());
  const [items, setItems] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .movements({ month: period })
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((caught) => {
        if (!cancelled) {
          notify.error(caught instanceof ApiError ? caught.message : 'No se pudo cargar.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, reloadToken, notify]);

  const totals = items.reduce(
    (acc, item) => {
      if (item.kind === 'income') acc.income += item.amount;
      if (item.kind === 'expense') acc.expense += item.amount;
      return acc;
    },
    { income: 0, expense: 0 },
  );

  const isCurrentMonth = period === currentPeriod();

  return (
    <div className="max-w-4xl mx-auto animate-rise">
      <PageHeader
        title="Movimientos"
        hint="Todo lo que registraste, mes a mes."
        action={
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPeriod(shiftMonth(period, -1))}
              aria-label="Mes anterior"
              className="grid place-items-center size-8 rounded-[7px] text-text-muted
                hover:text-text hover:bg-surface-hover transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="min-w-36 text-center text-[13px] font-medium capitalize">
              {monthLabel(period)}
            </span>
            <button
              type="button"
              onClick={() => setPeriod(shiftMonth(period, 1))}
              disabled={isCurrentMonth}
              aria-label="Mes siguiente"
              className="grid place-items-center size-8 rounded-[7px] text-text-muted
                hover:text-text hover:bg-surface-hover transition-colors
                disabled:opacity-30 disabled:pointer-events-none"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3 mb-6">
        <Total label="Ingresos" amount={totals.income} tone="positive" />
        <Total label="Gastos" amount={totals.expense} tone="negative" />
        <Total label="Balance" amount={totals.income - totals.expense} tone="auto" />
      </div>

      <Card padded={false}>
        {loading ? (
          <div className="py-14 text-center text-xs text-text-subtle">Cargando…</div>
        ) : (
          <ActivityList
            items={items}
            onDelete={onDelete}
            emptyTitle={`Sin movimientos en ${monthLabel(period)}`}
            emptyHint="Usa las flechas para revisar otro mes."
          />
        )}
      </Card>
    </div>
  );
}

function Total({
  label,
  amount,
  tone,
}: {
  label: string;
  amount: number;
  tone: 'positive' | 'negative' | 'auto';
}) {
  return (
    <Card>
      <p className="text-[11px] font-medium text-text-subtle uppercase tracking-wide">
        {label}
      </p>
      <Money amount={amount} tone={tone} className="block text-lg font-semibold mt-1.5" />
    </Card>
  );
}

function shiftMonth(period: string, delta: number): string {
  const [year, month] = period.split('-').map(Number);
  const shifted = new Date(year, month - 1 + delta, 1);
  return `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, '0')}`;
}
