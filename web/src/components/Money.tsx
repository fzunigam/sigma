import { formatCurrency, money, signedMoney } from '../lib/format';

type Tone = 'auto' | 'neutral' | 'positive' | 'negative';
type Currency = 'CLP' | 'USD';

interface Props {
  amount: number;
  /** `auto` colours by sign; `neutral` never colours. */
  tone?: Tone;
  /** Always show a leading + or −. */
  signed?: boolean;
  className?: string;
}

/**
 * Every amount in the app renders through here, so colour always means the same
 * thing: green is money coming in, red is money going out, and anything that is
 * merely a total stays neutral.
 */
export function Money({ amount, tone = 'neutral', signed = false, className = '' }: Props) {
  const resolved =
    tone === 'auto' ? (amount > 0 ? 'positive' : amount < 0 ? 'negative' : 'neutral') : tone;

  const colour =
    resolved === 'positive'
      ? 'text-positive'
      : resolved === 'negative'
        ? 'text-negative'
        : 'text-text';

  return (
    <span data-selectable className={`tnum ${colour} ${className}`}>
      {signed ? signedMoney(amount) : money(amount)}
    </span>
  );
}

interface CurrencyProps {
  amount: number;
  currency: Currency;
  tone?: Tone;
  signed?: boolean;
  className?: string;
}

/**
 * Like `Money`, but for Inversiones, the one place an amount can genuinely be
 * in USD instead of CLP. `Money` itself stays CLP-only everywhere else.
 */
export function CurrencyMoney({
  amount,
  currency,
  tone = 'neutral',
  signed = false,
  className = '',
}: CurrencyProps) {
  const resolved =
    tone === 'auto' ? (amount > 0 ? 'positive' : amount < 0 ? 'negative' : 'neutral') : tone;

  const colour =
    resolved === 'positive'
      ? 'text-positive'
      : resolved === 'negative'
        ? 'text-negative'
        : 'text-text';

  return (
    <span data-selectable className={`tnum ${colour} ${className}`}>
      {formatCurrency(amount, currency, signed)}
    </span>
  );
}
