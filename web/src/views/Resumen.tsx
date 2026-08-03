import { CreditCard, TrendingUp, Wallet } from 'lucide-react';
import { Card, SectionHeader } from '../components/Card';
import { ActivityList } from '../components/ActivityList';
import { Money } from '../components/Money';
import { RegistrarForm } from './RegistrarForm';
import { ConciliarCard } from './ConciliarCard';
import { money, monthLabel } from '../lib/format';
import type { Account, Activity, Summary } from '../lib/types';

interface Props {
  summary: Summary;
  onChanged: () => void;
  onEdit: (item: Activity) => void;
  notify: { success: (text: string) => void; error: (text: string) => void };
  onGoToAccounts: () => void;
}

export function Resumen({ summary, onChanged, onEdit, notify, onGoToAccounts }: Props) {
  const { totals, month, accounts } = summary;
  const hasCards = accounts.some((account) => account.kind === 'credit');

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-rise">
      {/* The three numbers that answer "how am I doing" without any clicking. */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          label="Disponible"
          amount={totals.available}
          hint="En cuentas y efectivo"
        />
        <Stat
          label={hasCards ? 'Después de pagar tarjetas' : 'Total'}
          amount={totals.net}
          hint={hasCards ? `Deuda en tarjetas: ${money(totals.debt)}` : 'Tu saldo real'}
          emphasis
        />
        <Stat
          label={`Balance de ${monthLabel(month.period)}`}
          amount={month.net}
          tone="auto"
          hint={`Ingresos ${abbreviate(month.income)} · Gastos ${abbreviate(month.expense)}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px] items-start">
        <div className="space-y-6 min-w-0">
          <Card padded={false}>
            <SectionHeader title="Últimos movimientos" className="p-5 pb-4" />
            <ActivityList
              items={summary.recent}
              onEdit={onEdit}
              emptyTitle="Todavía no hay movimientos"
              emptyHint="Registra tu primer gasto o ingreso con el formulario de la derecha."
            />
          </Card>

          <Card padded={false}>
            <SectionHeader title="Cuentas" className="p-5 pb-4" />
            {accounts.length === 0 ? (
              <p className="px-5 pb-5 text-xs text-text-subtle">
                Aún no tienes cuentas.{' '}
                <button
                  type="button"
                  onClick={onGoToAccounts}
                  className="text-accent hover:underline"
                >
                  Crear la primera
                </button>
                .
              </p>
            ) : (
              <ul className="divide-y divide-line">
                {accounts.map((account) => (
                  <AccountRow key={account.id} account={account} />
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <RegistrarForm summary={summary} onChanged={onChanged} notify={notify} />
          <ConciliarCard summary={summary} onChanged={onChanged} notify={notify} />
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  amount,
  hint,
  tone = 'neutral',
  emphasis = false,
}: {
  label: string;
  amount: number;
  hint?: string;
  tone?: 'neutral' | 'auto';
  emphasis?: boolean;
}) {
  return (
    <Card className={emphasis ? 'ring-1 ring-accent/20' : ''}>
      <p className="text-[11px] font-medium text-text-subtle uppercase tracking-wide">
        {label}
      </p>
      <Money amount={amount} tone={tone} className="block text-2xl font-semibold mt-2" />
      {hint && <p className="text-[11px] text-text-subtle mt-1.5">{hint}</p>}
    </Card>
  );
}

function AccountRow({ account }: { account: Account }) {
  const isCard = account.kind === 'credit';
  const isInvestment = account.kind === 'investment';
  const usage =
    isCard && account.credit_limit > 0
      ? Math.min(Math.round((account.balance / account.credit_limit) * 100), 100)
      : null;
  const shown = isInvestment ? (account.total_value_clp ?? account.balance) : account.balance;

  return (
    <li className="flex items-center gap-3 px-5 py-3">
      <span
        className="grid place-items-center size-7 rounded-full shrink-0
          bg-surface-hover text-text-subtle"
      >
        {isCard ? (
          <CreditCard size={13} />
        ) : isInvestment ? (
          <TrendingUp size={13} />
        ) : (
          <Wallet size={13} />
        )}
      </span>

      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium truncate">{account.name}</p>
        <p className="text-[11px] text-text-subtle">
          {isCard
            ? usage === null
              ? 'Sin cupo definido'
              : `${usage}% del cupo usado`
            : isInvestment
              ? 'Cuenta de inversión'
              : 'Cuenta de saldo'}
        </p>
      </div>

      <div className="text-right shrink-0">
        <Money amount={shown} className="block text-[13px] font-medium" />
        {isCard && account.credit_limit > 0 && (
          <p className="text-[11px] text-text-subtle mt-0.5">
            Disponible <Money amount={account.available} className="text-[11px]" />
          </p>
        )}
      </div>
    </li>
  );
}

function abbreviate(amount: number): string {
  if (amount === 0) return '$0';
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1).replace('.0', '')}M`;
  if (amount >= 1_000) return `$${Math.round(amount / 1_000)}K`;
  return `$${amount}`;
}
