export type AccountKind = 'debit' | 'credit' | 'investment';
export type MovementKind = 'expense' | 'income';
export type Currency = 'CLP' | 'USD';

export interface Account {
  id: string;
  name: string;
  kind: AccountKind;
  balance: number;
  credit_limit: number;
  available: number;
  created_at: string;
  deleted_at: string | null;
  /** Only present for `kind: 'investment'`: cash + holdings at the last
   * cached price, in CLP. `balance` alone is just its CLP cash. */
  total_value_clp?: number;
}

/** The fields an edit may change. Anything left out stays as it was. */
export interface MovementEdit {
  kind?: MovementKind;
  amount?: number;
  description?: string;
  account_id?: string;
  date?: string;
  pending?: boolean;
}

export interface TransferEdit {
  from_account?: string;
  to_account?: string;
  amount?: number;
  description?: string;
  date?: string;
}

/** A movement or a transfer, as shown on the shared activity timeline. */
export interface Activity {
  id: string;
  record: 'movement' | 'transfer';
  kind: MovementKind | 'transfer';
  amount: number;
  /** For a transfer this is the optional note; read it through `activityLabel`. */
  description: string;
  account_id: string;
  account_name: string;
  to_account_id: string | null;
  to_account_name: string | null;
  date: string;
  pending: number;
  reconciliation_id: string | null;
  created_at: string;
}

export interface Reconciliation {
  id: string;
  net_amount: number;
  movement_count: number;
  date: string;
  created_at: string;
}

export interface PendingMovement {
  id: string;
  kind: MovementKind;
  amount: number;
  description: string;
  account_id: string;
  account_name: string;
  date: string;
}

export interface Preferences {
  default_expense_account: string;
  default_income_account: string;
}

export interface Summary {
  accounts: Account[];
  totals: { available: number; debt: number; investments: number; net: number };
  pending: { net: number; count: number };
  month: { period: string; income: number; expense: number; net: number };
  recent: Activity[];
  reconciliations: Reconciliation[];
  preferences: Preferences;
}

// --- Inversiones -------------------------------------------------------------

export type InvestmentTransactionKind = 'buy' | 'sell' | 'dividend' | 'fx_exchange';

export interface Holding {
  account_id: string;
  ticker: string;
  quantity: number;
  avg_cost: number;
  currency: Currency;
}

export interface InvestmentTransaction {
  id: string;
  account_id: string;
  kind: InvestmentTransactionKind;
  ticker: string | null;
  quantity: number | null;
  price: number | null;
  fees: number;
  currency: Currency | null;
  clp_amount: number | null;
  usd_amount: number | null;
  realized_gain: number | null;
  date: string;
  created_at: string;
}

/** The fields correcting a buy or sell may change. */
export interface InvestmentTransactionEdit {
  quantity?: number;
  price?: number;
  fees?: number;
  date?: string;
}

export interface PositionMetric {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  currency: Currency;
  market_value_clp: number;
  cost_basis_clp: number;
  gain_clp: number;
  gain_pct: number | null;
  /** True when there is no cached price yet: shows the cost as a stand-in. */
  stale: boolean;
}

export interface AllocationSlice {
  label: string;
  value_clp: number;
}

export interface AccountMetrics {
  positions: PositionMetric[];
  cash_clp: number;
  cash_usd_clp: number;
  total_value_clp: number;
  unrealized_gain_clp: number;
  realized_gain_clp: number;
  dividends_clp: number;
  allocation: AllocationSlice[];
  /** Annualised money-weighted return, or `null` without enough history. */
  irr: number | null;
  /** `null` until prices have been refreshed at least once. */
  fx_rate: number | null;
}

export interface ValuePoint {
  date: string;
  value_clp: number;
}

export interface TickerQuote {
  price: number;
  currency: Currency;
  name: string;
}

export interface BackupFile {
  path: string;
  name: string;
  size: number;
}

export interface DatabaseStatus {
  path: string | null;
  name: string | null;
  folder: string | null;
  is_open: boolean;
  missing: boolean;
  locked_by: string | null;
  recent: { path: string; name: string }[];
  backups: BackupFile[];
  legacy_available: string | null;
  theme: 'dark' | 'light';
  version: string;
  migrated?: Record<string, number>;
}

export interface UpdateStatus {
  current: string;
  latest: string | null;
  available: boolean;
  url: string;
}

export interface InstalledUpdate {
  version: string;
  installed_at: string;
}
