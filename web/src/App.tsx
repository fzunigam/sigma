import { useCallback, useEffect, useState } from 'react';
import { Sidebar, type View } from './components/Sidebar';
import { Toaster, useToasts } from './components/Toaster';
import { Bienvenida } from './views/Bienvenida';
import { Resumen } from './views/Resumen';
import { Movimientos } from './views/Movimientos';
import { Cuentas } from './views/Cuentas';
import { Ajustes } from './views/Ajustes';
import { api, ApiError } from './lib/api';
import type { Activity, DatabaseStatus, Summary } from './lib/types';

export default function App() {
  const [database, setDatabase] = useState<DatabaseStatus | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [view, setView] = useState<View>('resumen');
  const [reloadToken, setReloadToken] = useState(0);
  const [booting, setBooting] = useState(true);
  const notify = useToasts();

  const loadDatabase = useCallback(async () => {
    const status = await api.databaseStatus();
    setDatabase(status);
    applyTheme(status.theme);
    return status;
  }, []);

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await api.summary());
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 400) {
        // The database went away underneath us; fall back to the setup screen.
        setSummary(null);
        await loadDatabase();
      } else {
        notify.error(caught instanceof ApiError ? caught.message : 'No se pudo cargar.');
      }
    }
  }, [loadDatabase, notify]);

  // First paint: find out whether a database is open, then load it.
  useEffect(() => {
    loadDatabase()
      .then((status) => (status.is_open ? loadSummary() : undefined))
      .finally(() => setBooting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Anything that writes calls this: reload the numbers and the month view. */
  const refresh = useCallback(() => {
    void loadSummary();
    setReloadToken((token) => token + 1);
  }, [loadSummary]);

  async function afterDatabaseChange(message?: string) {
    const status = await loadDatabase();
    if (status.is_open) await loadSummary();
    setReloadToken((token) => token + 1);
    if (message) notify.success(message);
  }

  async function toggleTheme() {
    if (!database) return;
    const next = database.theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    setDatabase({ ...database, theme: next });
    try {
      await api.setTheme(next);
    } catch {
      // Purely cosmetic: the theme is already applied, so a failed save is silent.
    }
  }

  async function deleteActivity(item: Activity) {
    try {
      if (item.record === 'transfer') await api.deleteTransfer(item.id);
      else await api.deleteMovement(item.id);
      notify.success('Movimiento eliminado.');
      refresh();
    } catch (caught) {
      notify.error(caught instanceof ApiError ? caught.message : 'No se pudo eliminar.');
    }
  }

  if (booting) {
    return <div className="h-full grid place-items-center text-xs text-text-subtle">…</div>;
  }

  if (!database || !database.is_open || !summary) {
    return (
      <>
        {database && (
          <Bienvenida status={database} onReady={(message) => afterDatabaseChange(message)} />
        )}
        <Toaster toasts={notify.toasts} onDismiss={notify.dismiss} />
      </>
    );
  }

  return (
    <div className="h-full flex">
      <Sidebar
        view={view}
        onNavigate={setView}
        database={database}
        theme={database.theme}
        onToggleTheme={toggleTheme}
      />

      <main className="flex-1 overflow-y-auto p-8">
        {view === 'resumen' && (
          <Resumen
            summary={summary}
            onChanged={refresh}
            onDelete={deleteActivity}
            notify={notify}
            onGoToAccounts={() => setView('cuentas')}
          />
        )}
        {view === 'movimientos' && (
          <Movimientos
            onDelete={deleteActivity}
            reloadToken={reloadToken}
            notify={notify}
          />
        )}
        {view === 'cuentas' && (
          <Cuentas summary={summary} onChanged={refresh} notify={notify} />
        )}
        {view === 'ajustes' && (
          <Ajustes
            database={database}
            onDatabaseChanged={() => afterDatabaseChange()}
            notify={notify}
          />
        )}
      </main>

      <Toaster toasts={notify.toasts} onDismiss={notify.dismiss} />
    </div>
  );
}

function applyTheme(theme: 'dark' | 'light') {
  document.documentElement.dataset.theme = theme;
}
