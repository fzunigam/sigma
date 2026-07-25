import { useState, type ReactNode } from 'react';
import { ArrowUpFromLine, FilePlus2, FolderOpen, Info } from 'lucide-react';
import { Input } from '../components/Field';
import { api, ApiError } from '../lib/api';
import * as bridge from '../lib/bridge';
import { shortPath } from '../lib/format';
import type { DatabaseStatus } from '../lib/types';

interface Props {
  status: DatabaseStatus;
  onReady: (message: string) => void;
}

type Action = 'create' | 'open' | 'migrate' | null;

/**
 * First run, and any time the selected file has gone missing. The whole screen
 * is one decision: which file holds your data.
 */
export function Bienvenida({ status, onReady }: Props) {
  const [busy, setBusy] = useState<Action>(null);
  const [error, setError] = useState('');
  const [manualPath, setManualPath] = useState('');
  const nativeDialogs = bridge.isAvailable();

  async function run(action: Exclude<Action, null>, pick: () => Promise<string | null>) {
    setError('');
    const path = await pick();
    if (!path) return;

    setBusy(action);
    try {
      if (action === 'create') {
        await api.createDatabase(path);
        onReady('Base de datos creada.');
      } else if (action === 'open') {
        await api.openDatabase(path);
        onReady('Base de datos abierta.');
      } else {
        const result = await api.migrateDatabase(path);
        const moved = result.migrated?.movements ?? 0;
        onReady(`Datos migrados: ${moved} movimientos.`);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo abrir el archivo.');
    } finally {
      setBusy(null);
    }
  }

  /** Native save dialog inside the app; a typed path when running in a browser. */
  const askWhereToSave = async () => {
    if (nativeDialogs) return bridge.chooseNewDatabase();
    if (manualPath.trim()) return manualPath.trim();
    setError('Escribe dónde guardar el archivo.');
    return null;
  };

  const askWhichToOpen = async () => {
    if (nativeDialogs) return bridge.chooseDatabase();
    if (manualPath.trim()) return manualPath.trim();
    setError('Escribe la ruta del archivo.');
    return null;
  };

  return (
    <div className="h-full overflow-y-auto grid place-items-center p-8">
      <div className="w-full max-w-md animate-rise">
        <header className="text-center mb-8">
          <span
            aria-hidden
            className="inline-grid place-items-center size-12 rounded-[14px]
              bg-accent-soft text-accent text-xl font-semibold mb-4"
          >
            Σ
          </span>
          <h1 className="text-lg font-semibold tracking-tight">
            {status.missing ? 'No encontramos tu base de datos' : 'Bienvenido a Sigma'}
          </h1>
          <p className="text-sm text-text-muted mt-1.5 leading-relaxed">
            {status.missing ? (
              <>
                El archivo{' '}
                <span className="text-text">{shortPath(status.path ?? '', 2)}</span> ya no está
                donde estaba. Vuelve a abrirlo o elige otro.
              </>
            ) : (
              'Tus datos viven en un solo archivo que tú eliges. Guárdalo en Google Drive y quedará respaldado solo.'
            )}
          </p>
        </header>

        <div className="space-y-2.5">
          {status.legacy_available && (
            <Option
              icon={<ArrowUpFromLine size={16} />}
              title="Traer mis datos de la versión anterior"
              hint="Copia tus cuentas y movimientos al archivo nuevo. La base antigua no se toca."
              highlighted
              loading={busy === 'migrate'}
              disabled={busy !== null}
              onClick={() => run('migrate', askWhereToSave)}
            />
          )}

          <Option
            icon={<FilePlus2 size={16} />}
            title="Crear una base de datos nueva"
            hint="Empezar de cero con un archivo vacío."
            loading={busy === 'create'}
            disabled={busy !== null}
            onClick={() => run('create', askWhereToSave)}
          />

          <Option
            icon={<FolderOpen size={16} />}
            title="Abrir una base de datos existente"
            hint="Usar un archivo que ya tienes, por ejemplo en Drive."
            loading={busy === 'open'}
            disabled={busy !== null}
            onClick={() => run('open', askWhichToOpen)}
          />
        </div>

        {status.recent.length > 0 && (
          <div className="mt-6">
            <p className="text-xs font-medium text-text-muted mb-2">Recientes</p>
            <div className="space-y-1">
              {status.recent.map((item) => (
                <button
                  key={item.path}
                  type="button"
                  disabled={busy !== null}
                  onClick={() => run('open', async () => item.path)}
                  className="flex items-baseline gap-2 w-full text-left px-3 py-2 rounded-[8px]
                    hover:bg-surface-hover transition-colors disabled:opacity-50"
                >
                  <span className="text-[13px]">{item.name}</span>
                  <span className="text-[11px] text-text-subtle truncate">
                    {shortPath(item.path, 2)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {!nativeDialogs && (
          <div className="mt-6 space-y-2">
            <label htmlFor="manual-path" className="block text-xs font-medium text-text-muted">
              Ruta del archivo
            </label>
            <Input
              id="manual-path"
              value={manualPath}
              onChange={(event) => setManualPath(event.target.value)}
              placeholder="/Users/tu-usuario/Drive/finanzas.db"
            />
            <p className="flex items-start gap-1.5 text-[11px] text-text-subtle">
              <Info size={12} className="mt-0.5 shrink-0" />
              Los diálogos del sistema solo están disponibles dentro de la aplicación.
            </p>
          </div>
        )}

        {error && (
          <p className="mt-5 text-xs text-negative bg-negative/10 border border-negative/20
            rounded-[8px] px-3 py-2.5">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

interface OptionProps {
  icon: ReactNode;
  title: string;
  hint: string;
  onClick: () => void;
  loading: boolean;
  disabled: boolean;
  highlighted?: boolean;
}

function Option({ icon, title, hint, onClick, loading, disabled, highlighted }: OptionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-start gap-3 w-full text-left p-4 rounded-[var(--radius-card)]
        border transition-all duration-150 disabled:opacity-50
        ${
          highlighted
            ? 'border-accent/35 bg-accent-soft hover:border-accent/60'
            : 'border-line bg-surface hover:border-line-strong hover:bg-surface-hover'
        }`}
    >
      <span
        className={`grid place-items-center size-8 rounded-[9px] shrink-0
          ${highlighted ? 'bg-accent/15 text-accent' : 'bg-surface-hover text-text-muted'}`}
      >
        {loading ? (
          <span className="size-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : (
          icon
        )}
      </span>
      <span className="min-w-0">
        <span className="block text-[13px] font-medium">{title}</span>
        <span className="block text-xs text-text-subtle mt-0.5 leading-relaxed">{hint}</span>
      </span>
    </button>
  );
}
