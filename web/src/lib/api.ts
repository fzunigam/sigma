import type {
  Account,
  Activity,
  DatabaseStatus,
  MovementEdit,
  MovementKind,
  PendingMovement,
  Preferences,
  Reconciliation,
  Summary,
  TransferEdit,
} from './types';

/**
 * The backend answers errors as `{ detail: "..." }` with a message already
 * written for the person reading it, so it is surfaced unchanged.
 */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    });
  } catch {
    throw new ApiError('No se pudo conectar con Sigma. Reinicia la aplicación.', 0);
  }

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(readDetail(body) ?? 'Ocurrió un error inesperado.', response.status);
  }
  return body as T;
}

/** FastAPI reports validation failures as a list; take the first message. */
function readDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    return first.msg ?? null;
  }
  return null;
}

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
const put = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(body) });
const patch = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
const remove = (path: string) => request<void>(path, { method: 'DELETE' });

export const api = {
  // Database file
  databaseStatus: () => request<DatabaseStatus>('/api/database'),
  createDatabase: (path: string) => post<DatabaseStatus>('/api/database/create', { path }),
  openDatabase: (path: string) => post<DatabaseStatus>('/api/database/open', { path }),
  migrateDatabase: (path: string) => post<DatabaseStatus>('/api/database/migrate', { path }),
  restoreBackup: (path: string) => post<DatabaseStatus>('/api/database/restore', { path }),
  setTheme: (theme: 'dark' | 'light') => put<{ theme: string }>('/api/theme', { theme }),

  // Overview
  summary: (month?: string) =>
    request<Summary>(`/api/summary${month ? `?month=${month}` : ''}`),

  // Accounts
  accounts: () => request<Account[]>('/api/accounts'),
  createAccount: (payload: {
    id: string;
    name: string;
    kind: Account['kind'];
    balance?: number;
    credit_limit?: number;
  }) => post<Account>('/api/accounts', payload),
  updateAccount: (id: string, payload: { name?: string; credit_limit?: number }) =>
    patch<Account>(`/api/accounts/${encodeURIComponent(id)}`, payload),
  renameAccountId: (id: string, newId: string) =>
    put<Account>(`/api/accounts/${encodeURIComponent(id)}/id`, { id: newId }),
  deleteAccount: (id: string) => remove(`/api/accounts/${encodeURIComponent(id)}`),

  // Movements
  movements: (params: { month?: string; limit?: number; search?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.month) query.set('month', params.month);
    if (params.limit) query.set('limit', String(params.limit));
    if (params.search) query.set('search', params.search);
    const suffix = query.toString();
    return request<Activity[]>(`/api/movements${suffix ? `?${suffix}` : ''}`);
  },
  createMovement: (payload: {
    kind: MovementKind;
    amount: number;
    description: string;
    account_id?: string | null;
    date?: string | null;
    pending?: boolean;
  }) => post<Activity>('/api/movements', payload),
  updateMovement: (id: string, payload: MovementEdit) =>
    patch<Activity>(`/api/movements/${id}`, payload),
  setMovementPending: (id: string, pending: boolean) =>
    put<Activity>(`/api/movements/${id}/pending`, { pending }),
  deleteMovement: (id: string) => remove(`/api/movements/${id}`),

  // Transfers
  createTransfer: (payload: {
    from_account: string;
    to_account: string;
    amount: number;
    description?: string;
    date?: string | null;
  }) => post<Activity>('/api/transfers', payload),
  updateTransfer: (id: string, payload: TransferEdit) =>
    patch<Activity>(`/api/transfers/${id}`, payload),
  deleteTransfer: (id: string) => remove(`/api/transfers/${id}`),

  // Reconciliations
  reconciliations: () => request<Reconciliation[]>('/api/reconciliations'),
  pending: () =>
    request<{ summary: { net: number; count: number }; movements: PendingMovement[] }>(
      '/api/reconciliations/pending',
    ),
  reconcile: () => post<Reconciliation>('/api/reconciliations'),
  reconciliationMovements: (id: string) =>
    request<PendingMovement[]>(`/api/reconciliations/${id}/movements`),

  // Preferences
  savePreferences: (payload: Preferences) => put<Preferences>('/api/preferences', payload),
};
