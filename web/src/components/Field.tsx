import { forwardRef } from 'react';
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';
import { dateInputLabel, plainNumber } from '../lib/format';

const CONTROL = `w-full h-9 px-3 bg-canvas border border-line rounded-[var(--radius-control)]
  text-sm text-text placeholder:text-text-subtle transition-colors
  hover:border-line-strong focus:border-accent focus:outline-none
  disabled:opacity-50`;

interface LabelProps {
  label: string;
  htmlFor: string;
  hint?: string;
  children: ReactNode;
}

export function Field({ label, htmlFor, hint, children }: LabelProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-xs font-medium text-text-muted">
        {label}
      </label>
      {children}
      {hint && <p className="text-[11px] text-text-subtle">{hint}</p>}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = '', ...rest }, ref) {
    return <input {...rest} ref={ref} className={`${CONTROL} ${className}`} />;
  },
);

/**
 * A date field shown as DD/MM/AAAA. The native picker renders its text in
 * whatever order the OS locale dictates (often MM/DD), so that text is made
 * invisible and a Chilean-order label is drawn on top; the calendar icon and
 * picker underneath are untouched.
 */
export const DateInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function DateInput({ className = '', value = '', disabled, ...rest }, ref) {
    return (
      <div className="relative">
        <input
          {...rest}
          ref={ref}
          type="date"
          value={value}
          disabled={disabled}
          className={`${CONTROL} ${className} text-transparent caret-transparent`}
        />
        <span
          className={`pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm tnum
            ${disabled ? 'text-text-subtle opacity-50' : 'text-text'}`}
        >
          {dateInputLabel(String(value))}
        </span>
      </div>
    );
  },
);

interface AmountProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> {
  /** Digits only, no separators: what gets sent to the API. */
  value: string;
  onValueChange: (digits: string) => void;
}

/**
 * A money input: right-aligned, tabular and digits-only. Thousands are grouped
 * as you type, because `1250000` and `125000` are indistinguishable at a glance
 * and getting a zero wrong is the easiest mistake to make in the whole app.
 */
export const AmountInput = forwardRef<HTMLInputElement, AmountProps>(function AmountInput(
  { className = '', value, onValueChange, ...rest },
  ref,
) {
  return (
    <div className="relative">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-text-subtle">
        $
      </span>
      <input
        {...rest}
        ref={ref}
        value={value ? plainNumber(Number(value)) : ''}
        onChange={(event) => onValueChange(onlyDigits(event.target.value))}
        inputMode="numeric"
        className={`${CONTROL} pl-7 tnum text-right font-medium ${className}`}
      />
    </div>
  );
});

/** Digits, without leading zeros, capped well below the safe-integer limit. */
function onlyDigits(raw: string): string {
  return raw
    .replace(/\D/g, '')
    .replace(/^0+(?=\d)/, '')
    .slice(0, 12);
}

interface DecimalProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> {
  value: string;
  onValueChange: (value: string) => void;
}

/**
 * A plain decimal input: share quantities and per-share prices. Unlike
 * `AmountInput` these are not whole Chilean pesos — they can have a fractional
 * part and no thousands grouping applies to them.
 */
export const DecimalInput = forwardRef<HTMLInputElement, DecimalProps>(function DecimalInput(
  { className = '', value, onValueChange, ...rest },
  ref,
) {
  return (
    <input
      {...rest}
      ref={ref}
      value={value}
      onChange={(event) => onValueChange(onlyDecimal(event.target.value))}
      inputMode="decimal"
      className={`${CONTROL} tnum text-right ${className}`}
    />
  );
});

/** Digits and a single decimal point, up to 8 places after it. */
function onlyDecimal(raw: string): string {
  const cleaned = raw.replace(/[^0-9.]/g, '');
  const [head, ...rest] = cleaned.split('.');
  return rest.length ? `${head}.${rest.join('').slice(0, 8)}` : head;
}

export function Select({ className = '', ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...rest} className={`${CONTROL} pr-8 cursor-pointer ${className}`} />;
}

interface CheckboxProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: string;
}

export function Checkbox({ id, label, checked, onChange, hint }: CheckboxProps) {
  return (
    <label
      htmlFor={id}
      className="flex items-start gap-2.5 cursor-pointer group py-0.5 select-none"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 size-4 rounded-[4px] accent-[var(--accent)] cursor-pointer"
      />
      <span className="min-w-0">
        <span className="block text-xs text-text-muted group-hover:text-text transition-colors">
          {label}
        </span>
        {hint && <span className="block text-[11px] text-text-subtle mt-0.5">{hint}</span>}
      </span>
    </label>
  );
}

interface SegmentedProps<T extends string> {
  options: { value: T; label: string; icon?: ReactNode }[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
}

/** Two or three mutually exclusive choices, shown side by side. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: SegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="grid gap-1 p-1 bg-canvas border border-line rounded-[var(--radius-control)]"
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(option.value)}
            className={`flex items-center justify-center gap-1.5 h-7 rounded-[5px] text-xs
              font-medium transition-all duration-150
              ${
                active
                  ? 'bg-surface text-text shadow-[var(--shadow-card)]'
                  : 'text-text-subtle hover:text-text-muted'
              }`}
          >
            {option.icon}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
