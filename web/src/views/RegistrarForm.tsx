import { useEffect, useRef, useState, type FormEvent } from 'react';
import { AlertCircle, ArrowRight, Minus, Plus } from 'lucide-react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { AmountInput, Checkbox, Field, Input, Segmented, Select } from '../components/Field';
import { api, ApiError } from '../lib/api';
import { todayIso } from '../lib/format';
import type { Summary } from '../lib/types';

type Kind = 'expense' | 'income' | 'transfer';

const PLACEHOLDER: Record<Kind, string> = {
  expense: 'Supermercado',
  income: 'Sueldo',
  transfer: 'Pago tarjeta',
};

interface Props {
  summary: Summary;
  onChanged: () => void;
  notify: { success: (text: string) => void; error: (text: string) => void };
}

/**
 * Logging a movement is the thing this app is for, so the form is always on
 * screen — never behind a button — and needs only two fields to be usable:
 * amount and description. Everything else has a sensible default.
 */
export function RegistrarForm({ summary, onChanged, notify }: Props) {
  const [kind, setKind] = useState<Kind>('expense');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [account, setAccount] = useState('');
  const [target, setTarget] = useState('');
  const [date, setDate] = useState('');
  const [include, setInclude] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const amountField = useRef<HTMLInputElement>(null);

  const { accounts, preferences } = summary;
  // Transfers can only leave an account that holds money, never a card.
  const sources = kind === 'transfer' ? accounts.filter((a) => a.kind !== 'credit') : accounts;

  // Follow the configured default when switching between expense and income.
  useEffect(() => {
    const preferred =
      kind === 'expense'
        ? preferences.default_expense_account
        : kind === 'income'
          ? preferences.default_income_account
          : '';
    const exists = sources.some((item) => item.id === preferred);
    setAccount(exists ? preferred : (sources[0]?.id ?? ''));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, preferences, accounts]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');

    const value = Number(amount);
    if (!value) {
      setError('Escribe un monto.');
      return;
    }
    if (kind !== 'transfer' && !description.trim()) {
      setError('Escribe una descripción.');
      return;
    }
    if (kind === 'transfer' && (!account || !target || account === target)) {
      setError('Elige dos cuentas distintas.');
      return;
    }

    setSaving(true);
    try {
      if (kind === 'transfer') {
        await api.createTransfer({
          from_account: account,
          to_account: target,
          amount: value,
          description: description.trim(),
          date: date || null,
        });
        notify.success('Transferencia registrada.');
      } else {
        await api.createMovement({
          kind,
          amount: value,
          description: description.trim(),
          account_id: account || null,
          date: date || null,
          pending: include,
        });
        notify.success(kind === 'expense' ? 'Gasto registrado.' : 'Ingreso registrado.');
      }
      setAmount('');
      setDescription('');
      setDate('');
      amountField.current?.focus();
      onChanged();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo guardar.');
    } finally {
      setSaving(false);
    }
  }

  const noAccounts = accounts.length === 0;

  return (
    <Card>
      <form onSubmit={submit} className="space-y-4">
        <Segmented
          ariaLabel="Tipo de movimiento"
          value={kind}
          onChange={(next) => {
            setKind(next);
            setError('');
          }}
          options={[
            { value: 'expense', label: 'Gasto', icon: <Minus size={12} /> },
            { value: 'income', label: 'Ingreso', icon: <Plus size={12} /> },
            { value: 'transfer', label: 'Traspaso', icon: <ArrowRight size={12} /> },
          ]}
        />

        <Field label="Monto" htmlFor="monto">
          <AmountInput
            id="monto"
            ref={amountField}
            value={amount}
            onValueChange={setAmount}
            placeholder="0"
            autoFocus
            disabled={noAccounts}
          />
        </Field>

        <Field
          label="Descripción"
          htmlFor="descripcion"
          hint={kind === 'transfer' ? 'Opcional.' : undefined}
        >
          <Input
            id="descripcion"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={PLACEHOLDER[kind]}
            maxLength={200}
            disabled={noAccounts}
          />
        </Field>

        <Field label={kind === 'transfer' ? 'Desde' : 'Cuenta'} htmlFor="cuenta">
          <Select
            id="cuenta"
            value={account}
            onChange={(event) => setAccount(event.target.value)}
            disabled={noAccounts}
          >
            {sources.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </Select>
        </Field>

        {kind === 'transfer' && (
          <Field label="Hacia" htmlFor="destino">
            <Select
              id="destino"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
            >
              <option value="">Elige una cuenta</option>
              {accounts
                .filter((item) => item.id !== account)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
            </Select>
          </Field>
        )}

        <Field label="Fecha" htmlFor="fecha">
          <Input
            id="fecha"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            max={todayIso()}
            disabled={noAccounts}
          />
        </Field>

        {kind !== 'transfer' && (
          <Checkbox
            id="incluir"
            label="Incluir en la conciliación"
            checked={include}
            onChange={setInclude}
          />
        )}

        {error && (
          <p className="flex items-start gap-2 text-xs text-negative">
            <AlertCircle size={13} className="mt-0.5 shrink-0" />
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" full loading={saving} disabled={noAccounts}>
          {noAccounts ? 'Crea una cuenta primero' : 'Registrar'}
        </Button>
      </form>
    </Card>
  );
}
