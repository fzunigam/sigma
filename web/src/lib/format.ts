const CLP = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 });

const MONTH_NAMES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

/** `$1.240.500`, with the minus sign kept outside the symbol. */
export function money(amount: number): string {
  const sign = amount < 0 ? '−' : '';
  return `${sign}$${CLP.format(Math.abs(amount))}`;
}

/** Same as `money` but always shows the sign, for deltas. */
export function signedMoney(amount: number): string {
  if (amount === 0) return money(0);
  return `${amount > 0 ? '+' : '−'}$${CLP.format(Math.abs(amount))}`;
}

export function plainNumber(amount: number): string {
  return CLP.format(amount);
}

/** `2026-07-24` → `24 jul`, or `24 jul 2025` when it is not the current year. */
export function shortDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  if (!year || !month || !day) return iso;
  const label = `${day} ${MONTH_NAMES[month - 1].slice(0, 3)}`;
  return year === new Date().getFullYear() ? label : `${label} ${year}`;
}

/** `2026-07` → `julio 2026` */
export function monthLabel(period: string): string {
  const [year, month] = period.split('-').map(Number);
  if (!year || !month) return period;
  return `${MONTH_NAMES[month - 1]} ${year}`;
}

export function monthName(month: number): string {
  return MONTH_NAMES[month - 1];
}

export function currentPeriod(): string {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
}

export function todayIso(): string {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${today.getFullYear()}-${month}-${day}`;
}

/** `finanzas_2026-07-24_1830.db` → `24 jul, 18:30` */
export function backupLabel(name: string): string {
  const match = name.match(/(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})/);
  if (!match) return name;
  const [, year, month, day, hour, minute] = match;
  const date = shortDate(`${year}-${month}-${day}`);
  return `${date}, ${hour}:${minute}`;
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Shortens a long path for display: `…/Drive/Sigma/finanzas.db` */
export function shortPath(path: string, segments = 3): string {
  const parts = path.split('/').filter(Boolean);
  if (parts.length <= segments) return path;
  return `…/${parts.slice(-segments).join('/')}`;
}
