import { useState, type FormEvent } from 'react';
import { Minus, Plus } from 'lucide-react';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { AmountInput, Checkbox, Field, Input, Segmented, Select } from '../components/Field';
import { api, ApiError } from '../lib/api';
import { todayIso } from '../lib/format';
import type { Account, Activity, MovementKind } from '../lib/types';

interface Props {
  item: Activity;
  accounts: Account[];
  onClose: () => void;
  /** Called after a successful save or delete, with the message to show. */
  onDone: (message: string) => void;
}

/**
 * Correcting what was already registered: a wrong digit, the wrong account, a
 * date typed in a hurry. Deleting lives in here too, so a row on the timeline
 * offers one thing to click instead of two.
 */
export function EditarMovimiento({ item, accounts, onClose, onDone }: Props) {
  const isTransfer = item.record === 'transfer';
  const reconciled = item.reconciliation_id !== null;

  const [kind, setKind] = useState<MovementKind>(
    item.kind === 'income' ? 'income' : 'expense',
  );
  const [amount, setAmount] = useState(String(item.amount));
  const [description, setDescription] = useState(item.description);
  const [account, setAccount] = useState(item.account_id);
  const [target, setTarget] = useState(item.to_account_id ?? '');
  const [date, setDate] = useState(item.date);
  const [pending, setPending] = useState(item.pending === 1);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  // Money can only leave an account that holds it, never a card.
  const sources = isTransfer ? accounts.filter((one) => one.kind !== 'credit') : accounts;

  async function save(event: FormEvent) {
    event.preventDefault();
    setError('');

    const value = Number(amount);
    if (!value) {
      setError('Escribe un monto.');
      return;
    }
    if (!isTransfer && !description.trim()) {
      setError('Escribe una descripción.');
      return;
    }
    if (isTransfer && (!account || !target || account === target)) {
      setError('Elige dos cuentas distintas.');
      return;
    }

    setSaving(true);
    try {
      if (isTransfer) {
        await api.updateTransfer(item.id, {
          from_account: account,
          to_account: target,
          amount: value,
          description: description.trim(),
          date,
        });
      } else {
        await api.updateMovement(item.id, {
          kind,
          amount: value,
          description: description.trim(),
          account_id: account,
          date,
          ...(reconciled ? {} : { pending }),
        });
      }
      onDone('Movimiento actualizado.');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo guardar.');
      setSaving(false);
    }
  }

  async function remove() {
    try {
      if (isTransfer) await api.deleteTransfer(item.id);
      else await api.deleteMovement(item.id);
      onDone('Movimiento eliminado.');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo eliminar.');
      setConfirmingDelete(false);
    }
  }

  return (
    <Modal
      title={isTransfer ? 'Editar traspaso' : 'Editar movimiento'}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={saving} onClick={save}>
            Guardar
          </Button>
        </>
      }
    >
      <form onSubmit={save} className="space-y-4">
        {!isTransfer && (
          <Segmented
            ariaLabel="Tipo de movimiento"
            value={kind}
            onChange={setKind}
            options={[
              { value: 'expense', label: 'Gasto', icon: <Minus size={12} /> },
              { value: 'income', label: 'Ingreso', icon: <Plus size={12} /> },
            ]}
          />
        )}

        <Field label="Monto" htmlFor="editar-monto">
          <AmountInput id="editar-monto" value={amount} onValueChange={setAmount} />
        </Field>

        <Field
          label="Descripción"
          htmlFor="editar-descripcion"
          hint={isTransfer ? 'Opcional.' : undefined}
        >
          <Input
            id="editar-descripcion"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={isTransfer ? 'Pago tarjeta' : ''}
            maxLength={200}
          />
        </Field>

        <Field label={isTransfer ? 'Desde' : 'Cuenta'} htmlFor="editar-cuenta">
          <Select
            id="editar-cuenta"
            value={account}
            onChange={(event) => setAccount(event.target.value)}
          >
            {sources.map((one) => (
              <option key={one.id} value={one.id}>
                {one.name}
              </option>
            ))}
            {/* Keeps a deleted account readable instead of silently switching it. */}
            {!sources.some((one) => one.id === account) && (
              <option value={account}>{item.account_name}</option>
            )}
          </Select>
        </Field>

        {isTransfer && (
          <Field label="Hacia" htmlFor="editar-destino">
            <Select
              id="editar-destino"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
            >
              <option value="">Elige una cuenta</option>
              {accounts
                .filter((one) => one.id !== account)
                .map((one) => (
                  <option key={one.id} value={one.id}>
                    {one.name}
                  </option>
                ))}
            </Select>
          </Field>
        )}

        <Field label="Fecha" htmlFor="editar-fecha">
          <Input
            id="editar-fecha"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            max={todayIso()}
          />
        </Field>

        {!isTransfer &&
          (reconciled ? (
            <p className="text-[11px] text-text-subtle">
              Ya fue conciliado, así que no vuelve a quedar pendiente.
            </p>
          ) : (
            <Checkbox
              id="editar-incluir"
              label="Incluir en la conciliación"
              checked={pending}
              onChange={setPending}
            />
          ))}

        {error && <p className="text-xs text-negative">{error}</p>}

        <div className="pt-3 border-t border-line">
          {confirmingDelete ? (
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-text-muted">
                Se descuenta de los saldos y desaparece de la lista.
              </p>
              <div className="flex gap-2 shrink-0">
                <Button size="sm" onClick={() => setConfirmingDelete(false)}>
                  No
                </Button>
                <Button size="sm" variant="danger" onClick={remove}>
                  Eliminar
                </Button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="text-xs text-text-subtle hover:text-negative transition-colors"
            >
              {isTransfer ? 'Eliminar este traspaso' : 'Eliminar este movimiento'}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
