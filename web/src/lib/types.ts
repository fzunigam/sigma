export type AccountKind = 'debit' | 'credit';
export type MovementKind = 'expense' | 'income';

export interface Account {
  id: string;
  name: string;
  kind: AccountKind;
  balance: number;
  credit_limit: number;
  available: number;
  created_at: string;
  deleted_at: string | null;
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
  totals: { available: number; debt: number; net: number };
  pending: { net: number; count: number };
  month: { period: string; income: number; expense: number; net: number };
  recent: Activity[];
  reconciliations: Reconciliation[];
  preferences: Preferences;
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
