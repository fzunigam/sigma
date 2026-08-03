import {
  ArrowLeftRight,
  LayoutGrid,
  Moon,
  Settings,
  Sun,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import { UpdateNotice } from './UpdateNotice';
import type { DatabaseStatus } from '../lib/types';

export type View = 'resumen' | 'movimientos' | 'cuentas' | 'inversiones' | 'ajustes';

const NAV: { id: View; label: string; icon: typeof LayoutGrid }[] = [
  { id: 'resumen', label: 'Resumen', icon: LayoutGrid },
  { id: 'movimientos', label: 'Movimientos', icon: ArrowLeftRight },
  { id: 'cuentas', label: 'Cuentas', icon: Wallet },
  { id: 'inversiones', label: 'Inversiones', icon: TrendingUp },
  { id: 'ajustes', label: 'Ajustes', icon: Settings },
];

interface Props {
  view: View;
  onNavigate: (view: View) => void;
  database: DatabaseStatus | null;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
}

export function Sidebar({ view, onNavigate, database, theme, onToggleTheme }: Props) {
  return (
    <aside
      className="w-56 shrink-0 flex flex-col border-r border-line bg-surface/40"
      // Leaves room for the traffic-light buttons of the native window.
      style={{ paddingTop: 'var(--titlebar-height, 28px)' }}
    >
      <div className="px-4 pt-2 pb-5">
        <div className="flex items-center gap-2.5 px-2">
          <span
            aria-hidden
            className="grid place-items-center size-7 rounded-[7px] bg-accent-soft
              text-accent font-semibold text-sm"
          >
            Σ
          </span>
          <span className="text-sm font-semibold tracking-tight">Sigma</span>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-0.5">
        {NAV.map(({ id, label, icon: Icon }) => {
          const active = view === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-2.5 w-full h-8 px-2.5 rounded-[7px]
                text-[13px] transition-colors duration-150
                ${
                  active
                    ? 'bg-surface-hover text-text font-medium'
                    : 'text-text-muted hover:text-text hover:bg-surface-hover/60'
                }`}
            >
              <Icon size={15} className={active ? 'text-accent' : ''} />
              {label}
            </button>
          );
        })}
      </nav>

      <footer className="p-3 border-t border-line">
        <UpdateNotice />
        <div className="flex items-center justify-between gap-2 px-1.5">
          <div className="min-w-0">
            <p className="text-[11px] font-medium truncate" title={database?.path ?? ''}>
              {database?.name ?? 'Sin base de datos'}
            </p>
            <p className="text-[10px] text-text-subtle">v{database?.version ?? '—'}</p>
          </div>
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === 'dark' ? 'Usar tema claro' : 'Usar tema oscuro'}
            className="shrink-0 text-text-subtle hover:text-text transition-colors p-1.5"
          >
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        </div>
      </footer>
    </aside>
  );
}
