import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { Card, PageHeader } from '../components/Card';
import { Money } from '../components/Money';
import { EmptyState } from '../components/EmptyState';
import { InversionCuenta } from './InversionCuenta';
import { api } from '../lib/api';
import type { Summary } from '../lib/types';

interface Props {
  summary: Summary;
  onChanged: () => void;
  notify: { success: (text: string) => void; error: (text: string) => void };
}

/**
 * Acciones y ETFs, al estilo Portfolio Performance. Always in the sidebar,
 * even with nothing set up yet, so it is discovered rather than hidden.
 */
export function Inversiones({ summary, onChanged, notify }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const accounts = summary.accounts.filter((account) => account.kind === 'investment');
  const selected = accounts.find((account) => account.id === selectedId) ?? null;

  // Refresh prices once, when the screen is opened — the only place
  // Inversiones touches the network, and it never blocks the view.
  useEffect(() => {
    api.investments
      .refresh()
      .then(() => onChanged())
      .catch(() => {
        // Best-effort: no internet just means the last cached prices stand.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (selected) {
    return (
      <InversionCuenta
        account={selected}
        onBack={() => setSelectedId(null)}
        onChanged={onChanged}
        notify={notify}
      />
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-rise">
      <PageHeader
        title="Inversiones"
        hint="Acciones y ETFs, con su valor al último precio conocido."
      />

      <Card padded={false}>
        {accounts.length === 0 ? (
          <EmptyState
            title="Todavía no tienes cuentas de inversión"
            hint="Créala desde Cuentas, eligiendo el tipo 'Inversión', y transfiérele plata desde tu cuenta corriente."
          />
        ) : (
          <ul className="divide-y divide-line">
            {accounts.map((account) => (
              <li key={account.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(account.id)}
                  className="flex w-full items-center gap-3 px-5 py-4 text-left
                    hover:bg-surface-hover transition-colors"
                >
                  <span
                    className="grid place-items-center size-8 rounded-[9px] shrink-0
                      bg-surface-hover text-text-subtle"
                  >
                    <TrendingUp size={14} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium truncate">{account.name}</p>
                    <p className="text-[11px] text-text-subtle">Ver posiciones y métricas</p>
                  </div>
                  <Money
                    amount={account.total_value_clp ?? account.balance}
                    className="text-[13px] font-medium shrink-0"
                  />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
