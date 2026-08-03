import { useState, type FormEvent } from 'react';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { DateInput, DecimalInput, Field, Input, Select } from '../components/Field';
import { api, ApiError } from '../lib/api';
import { todayIso } from '../lib/format';
import type { Currency, Holding } from '../lib/types';

export type Notify = { success: (text: string) => void; error: (text: string) => void };

/** Fees are typed in whole currency units but stored in minor units (USD
 * cents; CLP has none) — see `sigma.db.investments.to_minor` on the backend. */
function toMinor(amount: number, currency: Currency): number {
  return currency === 'USD' ? Math.round(amount * 100) : Math.round(amount);
}

// --- Comprar -----------------------------------------------------------------

export function Comprar({
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
  const [tickerName, setTickerName] = useState('');
  const [currency, setCurrency] = useState<Currency>('USD');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [fees, setFees] = useState('');
  const [date, setDate] = useState(todayIso());
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);

  async function checkTicker() {
    const value = ticker.trim();
    if (!value) return;
    setChecking(true);
    try {
      const quote = await api.investments.lookup(value);
      setTicker(value.toUpperCase());
      setTickerName(quote.name);
      setCurrency(quote.currency);
      setPrice((current) => current || String(quote.price));
      setError('');
    } catch {
      setTickerName('');
      setError(`No se encontró el ticker '${value.toUpperCase()}'.`);
    } finally {
      setChecking(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!ticker.trim()) {
      setError('Escribe un ticker.');
      return;
    }
    if (!Number(quantity) || !Number(price)) {
      setError('Escribe la cantidad y el precio.');
      return;
    }

    setSaving(true);
    try {
      await api.investments.buy({
        account_id: accountId,
        ticker,
        quantity: Number(quantity),
        price: Number(price),
        currency,
        date,
        fees: toMinor(Number(fees || 0), currency),
      });
      notify.success('Compra registrada.');
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo registrar la compra.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Comprar"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={saving} onClick={submit}>
            Comprar
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <Field
          label="Ticker"
          htmlFor="compra-ticker"
          hint={checking ? 'Buscando…' : tickerName ? `${tickerName} · ${currency}` : 'Ej. AAPL, VOO.'}
        >
          <Input
            id="compra-ticker"
            value={ticker}
            onChange={(event) => {
              setTicker(event.target.value.toUpperCase());
              setTickerName('');
            }}
            onBlur={checkTicker}
            placeholder="AAPL"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Cantidad" htmlFor="compra-cantidad">
            <DecimalInput
              id="compra-cantidad"
              value={quantity}
              onValueChange={setQuantity}
              placeholder="0"
            />
          </Field>
          <Field label={`Precio (${currency})`} htmlFor="compra-precio">
            <DecimalInput id="compra-precio" value={price} onValueChange={setPrice} placeholder="0" />
          </Field>
        </div>

        <Field label={`Comisión (${currency}, opcional)`} htmlFor="compra-comision">
          <DecimalInput id="compra-comision" value={fees} onValueChange={setFees} placeholder="0" />
        </Field>

        <Field label="Fecha" htmlFor="compra-fecha">
          <DateInput
            id="compra-fecha"
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

// --- Vender --------------------------------------------------------------------

export function Vender({
  accountId,
  holdings,
  onClose,
  onDone,
  notify,
}: {
  accountId: string;
  holdings: Holding[];
  onClose: () => void;
  onDone: () => void;
  notify: Notify;
}) {
  const [ticker, setTicker] = useState(holdings[0]?.ticker ?? '');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [fees, setFees] = useState('');
  const [date, setDate] = useState(todayIso());
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const holding = holdings.find((item) => item.ticker === ticker);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!holding) {
      setError('Elige un ticker.');
      return;
    }
    if (!Number(quantity) || !Number(price)) {
      setError('Escribe la cantidad y el precio.');
      return;
    }

    setSaving(true);
    try {
      await api.investments.sell({
        account_id: accountId,
        ticker,
        quantity: Number(quantity),
        price: Number(price),
        date,
        fees: toMinor(Number(fees || 0), holding.currency),
      });
      notify.success('Venta registrada.');
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo registrar la venta.');
    } finally {
      setSaving(false);
    }
  }

  if (holdings.length === 0) {
    return (
      <Modal title="Vender" onClose={onClose} footer={<Button onClick={onClose}>Cerrar</Button>}>
        <p className="text-xs text-text-subtle">Todavía no tienes posiciones para vender.</p>
      </Modal>
    );
  }

  return (
    <Modal
      title="Vender"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={saving} onClick={submit}>
            Vender
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <Field
          label="Ticker"
          htmlFor="venta-ticker"
          hint={holding ? `Tienes ${holding.quantity} a costo promedio ${holding.avg_cost}` : undefined}
        >
          <Select id="venta-ticker" value={ticker} onChange={(event) => setTicker(event.target.value)}>
            {holdings.map((item) => (
              <option key={item.ticker} value={item.ticker}>
                {item.ticker}
              </option>
            ))}
          </Select>
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Cantidad" htmlFor="venta-cantidad">
            <DecimalInput
              id="venta-cantidad"
              value={quantity}
              onValueChange={setQuantity}
              placeholder="0"
            />
          </Field>
          <Field label={`Precio (${holding?.currency ?? ''})`} htmlFor="venta-precio">
            <DecimalInput id="venta-precio" value={price} onValueChange={setPrice} placeholder="0" />
          </Field>
        </div>

        <Field label={`Comisión (${holding?.currency ?? ''}, opcional)`} htmlFor="venta-comision">
          <DecimalInput id="venta-comision" value={fees} onValueChange={setFees} placeholder="0" />
        </Field>

        <Field label="Fecha" htmlFor="venta-fecha">
          <DateInput
            id="venta-fecha"
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
