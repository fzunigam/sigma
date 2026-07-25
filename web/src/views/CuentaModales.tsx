import { useState, type FormEvent } from 'react';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { AmountInput, Field, Input, Segmented } from '../components/Field';
import { api, ApiError } from '../lib/api';
import { money } from '../lib/format';
import type { Account } from '../lib/types';

export type Notify = { success: (text: string) => void; error: (text: string) => void };

// --- Create ----------------------------------------------------------------

export function NuevaCuenta({
  onClose,
  onDone,
  notify,
}: {
  onClose: () => void;
  onDone: () => void;
  notify: Notify;
}) {
  const [name, setName] = useState('');
  const [kind, setKind] = useState<Account['kind']>('debit');
  const [balance, setBalance] = useState('');
  const [limit, setLimit] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!name.trim()) {
      setError('Escribe un nombre.');
      return;
    }

    setSaving(true);
    try {
      await api.createAccount({
        id: slug(name),
        name: name.trim(),
        kind,
        balance: kind === 'debit' ? Number(balance || 0) : 0,
        credit_limit: kind === 'credit' ? Number(limit || 0) : 0,
      });
      notify.success('Cuenta creada.');
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo crear la cuenta.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Nueva cuenta"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={saving} onClick={submit}>
            Crear
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nombre" htmlFor="nueva-nombre">
          <Input
            id="nueva-nombre"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Cuenta corriente"
          />
        </Field>

        <Field label="Tipo" htmlFor="nueva-tipo">
          <Segmented
            ariaLabel="Tipo de cuenta"
            value={kind}
            onChange={setKind}
            options={[
              { value: 'debit', label: 'Saldo' },
              { value: 'credit', label: 'Tarjeta de crédito' },
            ]}
          />
        </Field>

        {kind === 'debit' ? (
          <Field label="Saldo actual" htmlFor="nueva-saldo" hint="Cuánto tienes hoy.">
            <AmountInput
              id="nueva-saldo"
              value={balance}
              onChange={(event) => setBalance(event.target.value.replace(/\D/g, ''))}
              placeholder="0"
            />
          </Field>
        ) : (
          <Field label="Cupo total" htmlFor="nueva-cupo" hint="El máximo que puedes gastar.">
            <AmountInput
              id="nueva-cupo"
              value={limit}
              onChange={(event) => setLimit(event.target.value.replace(/\D/g, ''))}
              placeholder="0"
            />
          </Field>
        )}

        {error && <p className="text-xs text-negative">{error}</p>}
      </form>
    </Modal>
  );
}

// --- Edit ------------------------------------------------------------------

export function EditarCuenta({
  account,
  onClose,
  onDone,
  notify,
}: {
  account: Account;
  onClose: () => void;
  onDone: () => void;
  notify: Notify;
}) {
  const [name, setName] = useState(account.name);
  const [limit, setLimit] = useState(String(account.credit_limit || ''));
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.updateAccount(account.id, {
        name: name.trim(),
        ...(account.kind === 'credit' ? { credit_limit: Number(limit || 0) } : {}),
      });
      notify.success('Cuenta actualizada.');
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo guardar.');
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    try {
      await api.deleteAccount(account.id);
      notify.success('Cuenta eliminada.');
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo eliminar.');
    }
  }

  return (
    <Modal
      title={account.name}
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
        <Field label="Nombre" htmlFor="editar-nombre">
          <Input
            id="editar-nombre"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>

        {account.kind === 'credit' && (
          <Field
            label="Cupo total"
            htmlFor="editar-cupo"
            hint={`Ya gastaste ${money(account.balance)} de este cupo.`}
          >
            <AmountInput
              id="editar-cupo"
              value={limit}
              onChange={(event) => setLimit(event.target.value.replace(/\D/g, ''))}
            />
          </Field>
        )}

        {error && <p className="text-xs text-negative">{error}</p>}

        <div className="pt-3 border-t border-line">
          {confirmingDelete ? (
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-text-muted">
                Sus movimientos se conservan, pero deja de aparecer al registrar.
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
              Eliminar esta cuenta
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}

/** Turns a display name into the short identifier the database uses. */
function slug(name: string): string {
  const base = name
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 40);
  return base || `cuenta_${Date.now().toString(36)}`;
}
