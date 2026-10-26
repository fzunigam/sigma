import { ArrowLeftRight, LayoutGrid, Moon, Settings, Sun, Wallet } from 'lucide-react';
import { Logo } from './Logo';
import { UpdateNotice } from './UpdateNotice';
import type { DatabaseStatus } from '../lib/types';

export type View = 'resumen' | 'movimientos' | 'cuentas' | 'ajustes';

// Shortcuts mirror the native menu (`sigma/native.py`).
const NAV: { id: View; label: string; icon: typeof LayoutGrid; key: string }[] = [
  { id: 'resumen', label: 'Resumen', icon: LayoutGrid, key: '1' },
  { id: 'movimientos', label: 'Movimientos', icon: ArrowLeftRight, key: '2' },
  { id: 'cuentas', label: 'Cuentas', icon: Wallet, key: '3' },
  { id: 'ajustes', label: 'Ajustes', icon: Settings, key: ',' },
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
      data-sidebar
      className="w-56 shrink-0 flex flex-col border-r border-line bg-surface/40"
      // Leaves room for the traffic-light buttons of the native window.
      style={{ paddingTop: 'var(--titlebar-height, 28px)' }}
    >
      <div className="px-4 pt-2 pb-5">
        <div className="flex items-center gap-2.5 px-2">
          <Logo size={28} />
          <span className="text-sm font-semibold tracking-tight">Sigma</span>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-0.5">
        {NAV.map(({ id, label, icon: Icon, key }) => {
          const active = view === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
              aria-current={active ? 'page' : undefined}
              title={`${label} (⌘${key})`}
              className={`group flex items-center gap-2.5 w-full h-8 px-2.5 rounded-[8px]
                active:scale-[0.98]
                text-body transition-all duration-150
                ${
                  active
                    ? 'bg-surface text-text font-medium shadow-[var(--shadow-card)] ring-1 ring-line'
                    : 'text-text-muted hover:text-text hover:bg-surface-hover/60'
                }`}
            >
              <Icon size={15} className={active ? 'text-accent' : ''} />
              <span className="flex-1 text-left">{label}</span>
              <kbd
                className="font-sans text-label text-text-subtle opacity-0 transition-opacity
                  group-hover:opacity-100"
              >
                ⌘{key}
              </kbd>
            </button>
          );
        })}
      </nav>

      <footer className="p-3 border-t border-line">
        <UpdateNotice />
        <div className="flex items-center justify-between gap-2 px-1.5">
          <div className="min-w-0">
            <p className="text-label font-medium truncate" title={database?.path ?? ''}>
              {database?.name ?? 'Sin base de datos'}
            </p>
            <p className="text-label text-text-subtle">v{database?.version ?? '—'}</p>
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
