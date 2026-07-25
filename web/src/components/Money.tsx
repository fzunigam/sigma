import { money, signedMoney } from '../lib/format';

type Tone = 'auto' | 'neutral' | 'positive' | 'negative';

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
