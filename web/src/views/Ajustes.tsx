import { useState } from 'react';
import { FolderOpen, History, ShieldCheck, TriangleAlert } from 'lucide-react';
import { Card, PageHeader, SectionHeader } from '../components/Card';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { api, ApiError } from '../lib/api';
import * as bridge from '../lib/bridge';
import { backupLabel, fileSize, shortPath } from '../lib/format';
import type { BackupFile, DatabaseStatus } from '../lib/types';

interface Props {
  database: DatabaseStatus;
  onDatabaseChanged: () => void;
  notify: { success: (text: string) => void; error: (text: string) => void };
}

export function Ajustes({ database, onDatabaseChanged, notify }: Props) {
  const [switching, setSwitching] = useState(false);
  const [restoring, setRestoring] = useState<BackupFile | null>(null);

  async function switchDatabase() {
    const path = await bridge.chooseDatabase();
    if (!path) return;

    setSwitching(true);
    try {
      await api.openDatabase(path);
      notify.success('Base de datos cambiada.');
      onDatabaseChanged();
    } catch (caught) {
      notify.error(caught instanceof ApiError ? caught.message : 'No se pudo abrir.');
    } finally {
      setSwitching(false);
    }
  }

  async function openRecent(path: string) {
    try {
      await api.openDatabase(path);
      notify.success('Base de datos cambiada.');
      onDatabaseChanged();
    } catch (caught) {
      notify.error(caught instanceof ApiError ? caught.message : 'No se pudo abrir.');
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-rise">
      <PageHeader title="Ajustes" hint="Dónde viven tus datos y cómo se respaldan." />

      {database.locked_by && (
        <div
          className="flex items-start gap-3 p-4 rounded-[var(--radius-card)]
            border border-caution/30 bg-caution/10"
        >
          <TriangleAlert size={16} className="text-caution mt-0.5 shrink-0" />
          <div>
            <p className="text-[13px] font-medium">Este archivo está abierto en otro equipo</p>
            <p className="text-xs text-text-muted mt-1 leading-relaxed">
              Sigma lo detectó abierto en <span className="text-text">{database.locked_by}</span>
              . Si escribes desde los dos lados a la vez, la sincronización puede perder cambios.
              Cierra Sigma allá antes de seguir.
            </p>
          </div>
        </div>
      )}

      <Card>
        <SectionHeader
          title="Base de datos"
          hint="Todos tus datos están en este único archivo."
          action={
            <Button
              icon={<FolderOpen size={14} />}
              loading={switching}
              onClick={switchDatabase}
            >
              Cambiar
            </Button>
          }
        />

        <div className="mt-4 p-4 rounded-[var(--radius-control)] bg-canvas border border-line">
          <p className="text-[13px] font-medium">{database.name}</p>
          <p className="text-xs text-text-subtle mt-1 break-all" data-selectable>
            {database.path}
          </p>
          {database.path && bridge.isAvailable() && (
            <button
              type="button"
              onClick={() => bridge.revealInFinder(database.path!)}
              className="text-xs text-accent hover:underline mt-2"
            >
              Mostrar en Finder
            </button>
          )}
        </div>

        {database.recent.length > 1 && (
          <div className="mt-4">
            <p className="text-[11px] font-medium text-text-subtle uppercase tracking-wide mb-1.5">
              Otras bases recientes
            </p>
            <div className="space-y-0.5">
              {database.recent
                .filter((item) => item.path !== database.path)
                .map((item) => (
                  <button
                    key={item.path}
                    type="button"
                    onClick={() => openRecent(item.path)}
                    className="flex items-baseline gap-2 w-full text-left px-2.5 py-1.5
                      rounded-[6px] hover:bg-surface-hover transition-colors"
                  >
                    <span className="text-xs">{item.name}</span>
                    <span className="text-[11px] text-text-subtle truncate">
                      {shortPath(item.path, 2)}
                    </span>
                  </button>
                ))}
            </div>
          </div>
        )}
      </Card>

      <Card>
        <SectionHeader
          title="Respaldos automáticos"
          hint="Sigma copia el archivo cada vez que lo abre. Se guardan los últimos 10."
        />

        {database.backups.length === 0 ? (
          <p className="text-xs text-text-subtle mt-4">
            Todavía no hay respaldos. Se creará uno la próxima vez que abras esta base.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {database.backups.map((backup) => (
              <li key={backup.path} className="flex items-center gap-3 py-2.5">
                <History size={13} className="text-text-subtle shrink-0" />
                <span className="text-xs flex-1">{backupLabel(backup.name)}</span>
                <span className="text-[11px] text-text-subtle tnum">
                  {fileSize(backup.size)}
                </span>
                <Button size="sm" variant="ghost" onClick={() => setRestoring(backup)}>
                  Restaurar
                </Button>
              </li>
            ))}
          </ul>
        )}

        <p className="flex items-start gap-2 text-[11px] text-text-subtle mt-4">
          <ShieldCheck size={13} className="mt-px shrink-0" />
          Si guardas el archivo en Google Drive o Dropbox, además tendrás el historial de
          versiones de ese servicio.
        </p>
      </Card>

      <p className="text-center text-[11px] text-text-subtle">Sigma {database.version}</p>

      {restoring && (
        <RestaurarModal
          backup={restoring}
          onClose={() => setRestoring(null)}
          onDone={() => {
            setRestoring(null);
            onDatabaseChanged();
          }}
          notify={notify}
        />
      )}
    </div>
  );
}

function RestaurarModal({
  backup,
  onClose,
  onDone,
  notify,
}: {
  backup: BackupFile;
  onClose: () => void;
  onDone: () => void;
  notify: Props['notify'];
}) {
  const [working, setWorking] = useState(false);

  async function restore() {
    setWorking(true);
    try {
      await api.restoreBackup(backup.path);
      notify.success('Respaldo restaurado.');
      onDone();
    } catch (caught) {
      notify.error(caught instanceof ApiError ? caught.message : 'No se pudo restaurar.');
      setWorking(false);
    }
  }

  return (
    <Modal
      title="Restaurar respaldo"
      hint={`Volverás al estado del ${backupLabel(backup.name)}.`}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={working} onClick={restore}>
            Restaurar
          </Button>
        </>
      }
    >
      <p className="text-xs text-text-muted leading-relaxed">
        Todo lo registrado después de esa fecha desaparecerá de la base activa. Antes de
        reemplazarla, Sigma guarda un respaldo del estado actual, así que este paso también se
        puede deshacer.
      </p>
    </Modal>
  );
}
