import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Search, X } from 'lucide-react';
import { Card, PageHeader } from '../components/Card';
import { ActivityList } from '../components/ActivityList';
import { Money } from '../components/Money';
import { Input } from '../components/Field';
import { api, ApiError } from '../lib/api';
import { currentPeriod, monthLabel } from '../lib/format';
import type { Activity } from '../lib/types';

interface Props {
  onEdit: (item: Activity) => void;
  reloadToken: number;
  notify: { error: (text: string) => void };
}

/**
 * One month at a time, moved with the arrows. Typing in the search box drops the
 * month filter and looks across the whole history, because the question it
 * answers — "when did I pay this?" — is never about a month you already know.
 */
export function Movimientos({ onEdit, reloadToken, notify }: Props) {
  const [period, setPeriod] = useState(currentPeriod());
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  // Wait for a pause in the typing before asking the backend.
  useEffect(() => {
    const timer = setTimeout(() => setQuery(search.trim()), 200);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .movements(query ? { search: query } : { month: period })
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
  }, [period, query, reloadToken, notify]);

  const totals = items.reduce(
    (acc, item) => {
      if (item.kind === 'income') acc.income += item.amount;
      if (item.kind === 'expense') acc.expense += item.amount;
      return acc;
    },
    { income: 0, expense: 0 },
  );

  const searching = query !== '';

  return (
    <div className="max-w-4xl mx-auto animate-rise">
      <PageHeader
        title="Movimientos"
        hint={
          searching ? 'Buscando en todos los meses.' : 'Todo lo que registraste, mes a mes.'
        }
        action={<MonthPicker period={period} onChange={setPeriod} disabled={searching} />}
      />

      <div className="relative mb-4">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-text-subtle
            pointer-events-none"
        />
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Buscar por descripción o cuenta"
          aria-label="Buscar movimientos"
          className="pl-9 pr-9"
        />
        {search && (
          <button
            type="button"
            onClick={() => setSearch('')}
            aria-label="Limpiar la búsqueda"
            className="absolute right-2 top-1/2 -translate-y-1/2 grid place-items-center
              size-6 rounded-[5px] text-text-subtle hover:text-text
              hover:bg-surface-hover transition-colors"
          >
            <X size={13} />
          </button>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-3 mb-6">
        <Total label="Ingresos" amount={totals.income} tone="positive" />
        <Total label="Gastos" amount={totals.expense} tone="negative" />
        <Total label="Balance" amount={totals.income - totals.expense} tone="auto" />
      </div>

      <Card padded={false}>
        {loading ? (
          <div className="py-14 text-center text-xs text-text-subtle">Cargando…</div>
        ) : (
          <>
            {searching && items.length > 0 && (
              <p className="px-5 pt-4 text-[11px] text-text-subtle">
                {items.length} {items.length === 1 ? 'resultado' : 'resultados'} para “{query}”
              </p>
            )}
            <ActivityList
              items={items}
              onEdit={onEdit}
              emptyTitle={
                searching
                  ? `Nada que coincida con “${query}”`
                  : `Sin movimientos en ${monthLabel(period)}`
              }
              emptyHint={
                searching
                  ? 'Prueba con otra palabra, o con el nombre de la cuenta.'
                  : 'Usa las flechas para revisar otro mes.'
              }
            />
          </>
        )}
      </Card>
    </div>
  );
}

function MonthPicker({
  period,
  onChange,
  disabled,
}: {
  period: string;
  onChange: (period: string) => void;
  disabled: boolean;
}) {
  const arrow = `grid place-items-center size-8 rounded-[7px] text-text-muted
    hover:text-text hover:bg-surface-hover transition-colors
    disabled:opacity-30 disabled:pointer-events-none`;

  return (
    <div className={`flex items-center gap-1 ${disabled ? 'opacity-40' : ''}`}>
      <button
        type="button"
        onClick={() => onChange(shiftMonth(period, -1))}
        disabled={disabled}
        aria-label="Mes anterior"
        className={arrow}
      >
        <ChevronLeft size={16} />
      </button>
      <span className="min-w-36 text-center text-[13px] font-medium capitalize">
        {monthLabel(period)}
      </span>
      <button
        type="button"
        onClick={() => onChange(shiftMonth(period, 1))}
        disabled={disabled || period === currentPeriod()}
        aria-label="Mes siguiente"
        className={arrow}
      >
        <ChevronRight size={16} />
      </button>
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
