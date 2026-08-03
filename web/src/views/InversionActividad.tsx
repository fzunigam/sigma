import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Card, SectionHeader } from '../components/Card';
import { Button } from '../components/Button';
import { Money, CurrencyMoney } from '../components/Money';
import { EmptyState } from '../components/EmptyState';
import { api, ApiError } from '../lib/api';
import { shortDate } from '../lib/format';
import type { InvestmentTransaction } from '../lib/types';

type Notify = { success: (text: string) => void; error: (text: string) => void };

const TXN_LABEL: Record<InvestmentTransaction['kind'], string> = {
  buy: 'Compra',
  sell: 'Venta',
  dividend: 'Dividendo',
  fx_exchange: 'Cambio de moneda',
};

interface Props {
  items: InvestmentTransaction[];
  onChanged: () => void;
  notify: Notify;
}

/** Buys, sells, dividends and currency exchange for one account, newest
 * first. Editing an old one is not built yet — deleting and re-entering it
 * covers the same correction with a lot less interface. */
export function InversionActividad({ items, onChanged, notify }: Props) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  async function remove(id: string) {
    try {
      await api.investments.deleteTransaction(id);
      notify.success('Eliminado.');
      setConfirmingId(null);
      onChanged();
    } catch (caught) {
      notify.error(caught instanceof ApiError ? caught.message : 'No se pudo eliminar.');
    }
  }

  return (
    <Card padded={false}>
      <SectionHeader title="Actividad" className="p-5 pb-4" />
      {items.length === 0 ? (
        <EmptyState compact title="Todavía no hay movimientos en esta cuenta" />
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 px-5 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium">
                  {TXN_LABEL[item.kind]}
                  {item.ticker && ` · ${item.ticker}`}
                </p>
                <p className="text-[11px] text-text-subtle">{shortDate(item.date)}</p>
              </div>
              <TransactionAmount item={item} />
              {confirmingId === item.id ? (
                <div className="flex gap-1.5 shrink-0">
                  <Button size="sm" onClick={() => setConfirmingId(null)}>
                    No
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => remove(item.id)}>
                    Eliminar
                  </Button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmingId(item.id)}
                  aria-label="Eliminar"
                  className="shrink-0 grid place-items-center size-7 rounded-[6px]
                    text-text-subtle hover:text-negative hover:bg-surface-hover transition-colors"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function TransactionAmount({ item }: { item: InvestmentTransaction }) {
  if (item.kind === 'buy' || item.kind === 'sell') {
    const amount = (item.quantity ?? 0) * (item.price ?? 0);
    return (
      <CurrencyMoney
        amount={item.kind === 'buy' ? -amount : amount}
        currency={item.currency ?? 'CLP'}
        tone="auto"
        signed
        className="text-[13px] font-medium shrink-0"
      />
    );
  }
  if (item.kind === 'dividend') {
    // usd_amount is stored in cents; clp_amount is already whole pesos.
    const amount =
      item.currency === 'CLP' ? (item.clp_amount ?? 0) : (item.usd_amount ?? 0) / 100;
    return (
      <CurrencyMoney
        amount={amount}
        currency={item.currency ?? 'CLP'}
        tone="positive"
        signed
        className="text-[13px] font-medium shrink-0"
      />
    );
  }
  // fx_exchange: cash moving between the account's own currencies, not money
  // entering or leaving — neutral, the same treatment a transfer gets.
  return (
    <Money
      amount={item.clp_amount ?? 0}
      tone="neutral"
      className="text-[13px] font-medium shrink-0"
    />
  );
}
