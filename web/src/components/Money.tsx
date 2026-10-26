import { useEffect, useRef, useState } from 'react';
import { money, signedMoney } from '../lib/format';

type Tone = 'auto' | 'neutral' | 'positive' | 'negative';

interface Props {
  amount: number;
  /** `auto` colours by sign; `neutral` never colours. */
  tone?: Tone;
  /** Always show a leading + or −. */
  signed?: boolean;
  className?: string;
  /** Headline style: a smaller, quieter `$` so the digits carry the number. */
  figure?: boolean;
  /** Glide to a new value instead of jumping; for headline figures only. */
  animate?: boolean;
}

/**
 * Every amount in the app renders through here, so colour always means the same
 * thing: green is money coming in, red is money going out, and anything that is
 * merely a total stays neutral.
 */
export function Money({
  amount,
  tone = 'neutral',
  signed = false,
  className = '',
  animate = false,
  figure = false,
}: Props) {
  const shown = useGlide(amount, animate);
  const resolved =
    tone === 'auto' ? (amount > 0 ? 'positive' : amount < 0 ? 'negative' : 'neutral') : tone;

  const colour =
    resolved === 'positive'
      ? 'text-positive'
      : resolved === 'negative'
        ? 'text-negative'
        : 'text-text';

  const text = signed ? signedMoney(shown) : money(shown);

  return (
    <span data-selectable className={`tnum ${colour} ${className}`}>
      {figure ? <Figure text={text} /> : text}
    </span>
  );
}

/** Eases from the previous value to `target` over ~400ms. */
function useGlide(target: number, enabled: boolean): number {
  const [value, setValue] = useState(target);
  const from = useRef(target);

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!enabled || reduced || from.current === target) {
      from.current = target;
      setValue(target);
      return;
    }
    const start = performance.now();
    const origin = from.current;
    let frame = 0;
    const step = (now: number) => {
      const t = Math.min((now - start) / 400, 1);
      const eased = 1 - (1 - t) ** 3;
      setValue(Math.round(origin + (target - origin) * eased));
      if (t < 1) frame = requestAnimationFrame(step);
      else from.current = target;
    };
    frame = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frame);
      from.current = target;
    };
  }, [target, enabled]);

  return enabled ? value : target;
}

/** Splits `−$1.240.500` into sign, symbol and digits so the symbol can recede. */
function Figure({ text }: { text: string }) {
  const at = text.indexOf('$');
  return (
    <>
      {text.slice(0, at)}
      <span className="text-[0.58em] align-[0.42em] font-medium opacity-55 mr-[0.06em]">$</span>
      {text.slice(at + 1)}
    </>
  );
}
