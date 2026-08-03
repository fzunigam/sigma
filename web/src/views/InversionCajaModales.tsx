import { useState, type FormEvent } from 'react';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { AmountInput, DateInput, DecimalInput, Field, Input, Segmented } from '../components/Field';
import { api, ApiError } from '../lib/api';
import { todayIso } from '../lib/format';
import type { Currency } from '../lib/types';
import type { Notify } from './InversionModales';

// --- Dividendo -----------------------------------------------------------------

export function Dividendo({
  accountId,
  onClose,
  onDone,
  notify,
}: {
  accountId: string;
  onClose: () => void;
  onDone: () => void;
  notify: Notify;
}) {
  const [ticker, setTicker] = useState('');
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState<Currency>('USD');
  const [date, setDate] = useState(todayIso());
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!ticker.trim()) {
      setError('Escribe un ticker.');
      return;
    }
    if (!Number(amount)) {
      setError('Escribe un monto.');
      return;
    }

    setSaving(true);
    try {
      await api.investments.dividend({
        account_id: accountId,
        ticker: ticker.toUpperCase(),
        amount: Number(amount),
        currency,
        date,
      });
      notify.success('Dividendo registrado.');
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo registrar el dividendo.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Dividendo"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={saving} onClick={submit}>
            Registrar
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="Ticker" htmlFor="div-ticker">
          <Input
            id="div-ticker"
            value={ticker}
            onChange={(event) => setTicker(event.target.value.toUpperCase())}
            placeholder="AAPL"
          />
        </Field>

        <Field label="Moneda" htmlFor="div-moneda">
          <Segmented
            ariaLabel="Moneda del dividendo"
            value={currency}
            onChange={setCurrency}
            options={[
              { value: 'USD', label: 'Dólares' },
              { value: 'CLP', label: 'Pesos' },
            ]}
          />
        </Field>

        <Field label="Monto recibido" htmlFor="div-monto">
          <DecimalInput id="div-monto" value={amount} onValueChange={setAmount} placeholder="0" />
        </Field>

        <Field label="Fecha" htmlFor="div-fecha">
          <DateInput
            id="div-fecha"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            max={todayIso()}
          />
        </Field>

        {error && <p className="text-xs text-negative">{error}</p>}
      </form>
    </Modal>
  );
}

// --- Cambio de moneda ------------------------------------------------------------

export function CambioMoneda({
  accountId,
  onClose,
  onDone,
  notify,
}: {
  accountId: string;
  onClose: () => void;
  onDone: () => void;
  notify: Notify;
}) {
  const [clpAmount, setClpAmount] = useState('');
  const [usdAmount, setUsdAmount] = useState('');
  const [date, setDate] = useState(todayIso());
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const rate = Number(clpAmount) && Number(usdAmount) ? Number(clpAmount) / Number(usdAmount) : null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!Number(clpAmount) || !Number(usdAmount)) {
      setError('Escribe los dos montos.');
      return;
    }

    setSaving(true);
    try {
      await api.investments.fxExchange({
        account_id: accountId,
        clp_amount: Number(clpAmount),
        usd_amount: Number(usdAmount),
        date,
      });
      notify.success('Cambio de moneda registrado.');
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo registrar el cambio.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Cambio de moneda"
      hint="Convierte pesos a dólares dentro de la cuenta, al tipo de cambio que te cobraron."
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={saving} onClick={submit}>
            Convertir
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="Pesos que conviertes" htmlFor="fx-clp">
          <AmountInput id="fx-clp" value={clpAmount} onValueChange={setClpAmount} placeholder="0" />
        </Field>

        <Field
          label="Dólares que recibes"
          htmlFor="fx-usd"
          hint={rate ? `Tipo de cambio: ${rate.toFixed(2)} CLP/USD` : undefined}
        >
          <DecimalInput id="fx-usd" value={usdAmount} onValueChange={setUsdAmount} placeholder="0" />
        </Field>

        <Field label="Fecha" htmlFor="fx-fecha">
          <DateInput
            id="fx-fecha"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            max={todayIso()}
          />
        </Field>

        {error && <p className="text-xs text-negative">{error}</p>}
      </form>
    </Modal>
  );
}
