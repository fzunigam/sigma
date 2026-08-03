import { useEffect, useState } from 'react';
import { ArrowLeftRight, ChevronLeft, Plus, TrendingDown, TrendingUp } from 'lucide-react';
import { Card, PageHeader, SectionHeader } from '../components/Card';
import { Button } from '../components/Button';
import { Money } from '../components/Money';
import { EmptyState } from '../components/EmptyState';
import { PortafolioChart } from '../components/PortafolioChart';
import { Comprar, Vender } from './InversionModales';
import { Dividendo, CambioMoneda } from './InversionCajaModales';
import { InversionActividad } from './InversionActividad';
import { api, ApiError } from '../lib/api';
import { formatCurrency } from '../lib/format';
import type { Account, AccountMetrics, Holding, InvestmentTransaction, ValuePoint } from '../lib/types';

type Notify = { success: (text: string) => void; error: (text: string) => void };
type ModalKind = 'comprar' | 'vender' | 'dividendo' | 'cambio' | null;

interface Props {
  account: Account;
  onBack: () => void;
  onChanged: () => void;
  notify: Notify;
}

/**
 * The detail for one investment account: value, gain, dividends, IRR, the
 * portfolio chart, its positions and the transactions behind them. Buying,
 * selling, dividends and currency exchange all open from here.
 */
export function InversionCuenta({ account, onBack, onChanged, notify }: Props) {
  const [metrics, setMetrics] = useState<AccountMetrics | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [activity, setActivity] = useState<InvestmentTransaction[]>([]);
  const [history, setHistory] = useState<ValuePoint[]>([]);
  const [modal, setModal] = useState<ModalKind>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.investments.metrics(account.id),
      api.investments.holdings(account.id),
      api.investments.activity(account.id),
      api.investments.history(account.id),
    ])
      .then(([m, h, a, hist]) => {
        if (cancelled) return;
        setMetrics(m);
        setHoldings(h);
        setActivity(a);
        setHistory(hist);
      })
      .catch((caught) => {
        notify.error(
          caught instanceof ApiError ? caught.message : 'No se pudo cargar la cuenta.',
        );
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [account.id, reloadToken]);

  function afterTransaction() {
    setModal(null);
    setReloadToken((token) => token + 1);
    onChanged();
  }

  function afterActivityChange() {
    setReloadToken((token) => token + 1);
    onChanged();
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-rise">
      <PageHeader
        title={account.name}
        hint="Cuenta de inversión"
        action={
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1 text-xs text-text-muted hover:text-text"
          >
            <ChevronLeft size={14} /> Todas las cuentas
          </button>
        }
      />

      <div className="flex flex-wrap gap-2">
        <Button variant="primary" icon={<Plus size={14} />} onClick={() => setModal('comprar')}>
          Comprar
        </Button>
        <Button onClick={() => setModal('vender')}>Vender</Button>
        <Button onClick={() => setModal('dividendo')}>Dividendo</Button>
        <Button icon={<ArrowLeftRight size={14} />} onClick={() => setModal('cambio')}>
          Cambio de moneda
        </Button>
      </div>

      {metrics && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Valor total" amount={metrics.total_value_clp} />
            <Stat label="Ganancia no realizada" amount={metrics.unrealized_gain_clp} tone="auto" />
            <Stat label="Ganancia realizada" amount={metrics.realized_gain_clp} tone="auto" />
            <Stat
              label="Rentabilidad anualizada"
              text={metrics.irr !== null ? `${(metrics.irr * 100).toFixed(1)}%` : '—'}
              hint={metrics.irr === null ? 'Necesita al menos un traspaso a la cuenta' : undefined}
            />
          </div>

          <Card>
            <SectionHeader title="Evolución del valor" className="mb-2" />
            <PortafolioChart points={history} />
          </Card>

          <Card padded={false}>
            <SectionHeader title="Posiciones" className="p-5 pb-4" />
            {metrics.positions.length === 0 ? (
              <EmptyState
                compact
                title="Todavía no tienes posiciones"
                hint="Compra tu primer ticker con el botón de arriba."
              />
            ) : (
              <ul className="divide-y divide-line">
                {metrics.positions.map((position) => (
                  <li key={position.ticker} className="flex items-center gap-3 px-5 py-3">
                    <span
                      className="grid place-items-center size-7 rounded-full shrink-0
                        bg-surface-hover text-text-subtle"
                    >
                      {position.gain_clp >= 0 ? (
                        <TrendingUp size={13} />
                      ) : (
                        <TrendingDown size={13} />
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[13px] font-medium">{position.ticker}</p>
                      <p className="text-[11px] text-text-subtle">
                        {position.quantity} a {formatCurrency(position.current_price, position.currency)}
                        {position.stale && ' · sin precio actualizado'}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <Money
                        amount={position.market_value_clp}
                        className="block text-[13px] font-medium"
                      />
                      <Money
                        amount={position.gain_clp}
                        tone="auto"
                        signed
                        className="text-[11px] block mt-0.5"
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {metrics.allocation.length > 0 && (
            <Card>
              <SectionHeader title="Asignación" hint="Cuánto pesa cada parte del total." />
              <ul className="space-y-2 mt-4">
                {metrics.allocation.map((slice) => {
                  const pct = metrics.total_value_clp
                    ? Math.round((slice.value_clp / metrics.total_value_clp) * 100)
                    : 0;
                  return (
                    <li key={slice.label} className="space-y-1">
                      <div className="flex justify-between text-[12px]">
                        <span className="text-text-muted">{slice.label}</span>
                        <span className="tnum text-text-subtle">{pct}%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-surface-hover overflow-hidden">
                        <div className="h-full bg-accent rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </Card>
          )}

          <Card>
            <SectionHeader title="Dividendos recibidos" />
            <Money amount={metrics.dividends_clp} className="block text-xl font-semibold mt-2" />
          </Card>
        </>
      )}

      <InversionActividad items={activity} onChanged={afterActivityChange} notify={notify} />

      {modal === 'comprar' && (
        <Comprar
          accountId={account.id}
          onClose={() => setModal(null)}
          onDone={afterTransaction}
          notify={notify}
        />
      )}
      {modal === 'vender' && (
        <Vender
          accountId={account.id}
          holdings={holdings}
          onClose={() => setModal(null)}
          onDone={afterTransaction}
          notify={notify}
        />
      )}
      {modal === 'dividendo' && (
        <Dividendo
          accountId={account.id}
          onClose={() => setModal(null)}
          onDone={afterTransaction}
          notify={notify}
        />
      )}
      {modal === 'cambio' && (
        <CambioMoneda
          accountId={account.id}
          onClose={() => setModal(null)}
          onDone={afterTransaction}
          notify={notify}
        />
      )}
    </div>
  );
}

function Stat({
  label,
  amount,
  text,
  tone = 'neutral',
  hint,
}: {
  label: string;
  amount?: number;
  text?: string;
  tone?: 'neutral' | 'auto';
  hint?: string;
}) {
  return (
    <Card>
      <p className="text-[11px] font-medium text-text-subtle uppercase tracking-wide">{label}</p>
      {text !== undefined ? (
        <p className="text-2xl font-semibold mt-2 tnum">{text}</p>
      ) : (
        <Money
          amount={amount ?? 0}
          tone={tone}
          signed={tone === 'auto'}
          className="block text-2xl font-semibold mt-2"
        />
      )}
      {hint && <p className="text-[11px] text-text-subtle mt-1.5">{hint}</p>}
    </Card>
  );
}
