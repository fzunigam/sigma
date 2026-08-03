import { useState } from 'react';
import { CreditCard, MoreHorizontal, Plus, TrendingUp, Wallet } from 'lucide-react';
import { Card, PageHeader, SectionHeader } from '../components/Card';
import { Button } from '../components/Button';
import { Money } from '../components/Money';
import { EmptyState } from '../components/EmptyState';
import { Field, Select } from '../components/Field';
import { api, ApiError } from '../lib/api';
import { money } from '../lib/format';
import type { Account, AccountKind, Summary } from '../lib/types';
import { EditarCuenta, NuevaCuenta } from './CuentaModales';

const KIND_ICON: Record<AccountKind, typeof Wallet> = {
  debit: Wallet,
  credit: CreditCard,
  investment: TrendingUp,
};

function kindSubtitle(account: Account): string {
  if (account.kind === 'investment') return 'Cuenta de inversión';
  if (account.kind === 'credit') {
    return account.credit_limit > 0
      ? `Cupo total ${money(account.credit_limit)}`
      : 'Tarjeta de crédito · sin cupo definido';
  }
  return 'Cuenta de saldo';
}

interface Props {
  summary: Summary;
  onChanged: () => void;
  notify: { success: (text: string) => void; error: (text: string) => void };
}

export function Cuentas({ summary, onChanged, notify }: Props) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const { accounts, preferences } = summary;

  async function savePreferences(patch: Partial<typeof preferences>) {
    try {
      await api.savePreferences({ ...preferences, ...patch });
      notify.success('Preferencia guardada.');
      onChanged();
    } catch (caught) {
      notify.error(caught instanceof ApiError ? caught.message : 'No se pudo guardar.');
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-rise">
      <PageHeader
        title="Cuentas"
        hint="Dónde tienes tu dinero y cuánto puedes gastar."
        action={
          <Button variant="primary" icon={<Plus size={14} />} onClick={() => setCreating(true)}>
            Nueva cuenta
          </Button>
        }
      />

      <Card padded={false}>
        {accounts.length === 0 ? (
          <EmptyState
            title="Todavía no tienes cuentas"
            hint="Crea una cuenta para empezar a registrar movimientos."
            action={
              <Button variant="primary" onClick={() => setCreating(true)}>
                Crear cuenta
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-line">
            {accounts.map((account) => {
              const Icon = KIND_ICON[account.kind];
              const shown =
                account.kind === 'investment'
                  ? (account.total_value_clp ?? account.balance)
                  : account.balance;
              return (
                <li key={account.id} className="flex items-center gap-3 px-5 py-4">
                  <span
                    className="grid place-items-center size-8 rounded-[9px] shrink-0
                      bg-surface-hover text-text-subtle"
                  >
                    <Icon size={14} />
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium truncate">{account.name}</p>
                    <p className="text-[11px] text-text-subtle">{kindSubtitle(account)}</p>
                  </div>

                  <div className="text-right shrink-0 mr-1">
                    <Money amount={shown} className="block text-[13px] font-medium" />
                    <p className="text-[11px] text-text-subtle mt-0.5">
                      {account.kind === 'credit'
                        ? 'gastado'
                        : account.kind === 'investment'
                          ? 'valor total'
                          : 'disponible'}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => setEditing(account)}
                    aria-label={`Opciones de ${account.name}`}
                    className="grid place-items-center size-7 rounded-[6px] text-text-subtle
                      hover:text-text hover:bg-surface-hover transition-colors shrink-0"
                  >
                    <MoreHorizontal size={15} />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      {accounts.length > 0 && (
        <Card>
          <SectionHeader
            title="Cuentas por defecto"
            hint="Las que aparecen preseleccionadas al registrar."
          />
          <div className="grid gap-4 sm:grid-cols-2 mt-4">
            <Field label="Para gastos" htmlFor="default-expense">
              <Select
                id="default-expense"
                value={preferences.default_expense_account}
                onChange={(event) =>
                  savePreferences({ default_expense_account: event.target.value })
                }
              >
                <option value="">Sin preferencia</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Para ingresos" htmlFor="default-income">
              <Select
                id="default-income"
                value={preferences.default_income_account}
                onChange={(event) =>
                  savePreferences({ default_income_account: event.target.value })
                }
              >
                <option value="">Sin preferencia</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
        </Card>
      )}

      {creating && (
        <NuevaCuenta
          onClose={() => setCreating(false)}
          onDone={() => {
            setCreating(false);
            onChanged();
          }}
          notify={notify}
        />
      )}

      {editing && (
        <EditarCuenta
          account={editing}
          onClose={() => setEditing(null)}
          onDone={() => {
            setEditing(null);
            onChanged();
          }}
          notify={notify}
        />
      )}
    </div>
  );
}
