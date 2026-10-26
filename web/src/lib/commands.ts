/**
 * App-wide commands, reachable from the keyboard and from the native menu bar.
 *
 * Inside the app the menu (`sigma/native.py`) owns the shortcuts and sends a
 * `sigma:command` event; the keydown listener covers `npm run dev` in a browser.
 * When a menu shortcut is pressed the page sees the keydown first, handles it,
 * and stops it, so each press runs exactly once.
 */
import { useEffect, useRef } from 'react';

export type Command =
  | 'go:resumen'
  | 'go:movimientos'
  | 'go:cuentas'
  | 'go:ajustes'
  | 'new'
  | 'find';

const KEYS: Record<string, Command> = {
  '1': 'go:resumen',
  '2': 'go:movimientos',
  '3': 'go:cuentas',
  '4': 'go:ajustes',
  ',': 'go:ajustes',
  n: 'new',
  f: 'find',
};

export function useCommands(run: (command: Command) => void, enabled: boolean): void {
  const latest = useRef(run);
  latest.current = run;

  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (!event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) return;
      const command = KEYS[event.key.toLowerCase()];
      if (!command || dialogOpen()) return;
      event.preventDefault();
      latest.current(command);
    };
    const onCommand = (event: Event) => {
      const command = (event as CustomEvent<string>).detail;
      if (dialogOpen()) return;
      if (Object.values(KEYS).includes(command as Command)) latest.current(command as Command);
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('sigma:command', onCommand);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('sigma:command', onCommand);
    };
  }, [enabled]);
}

/** A dialog owns the keyboard until it closes. */
function dialogOpen(): boolean {
  return document.querySelector('[role="dialog"]') !== null;
}

/**
 * Focus the element marked `data-command-target={name}` once it is on screen.
 * A command may switch views first, so the target can take a frame to appear.
 */
export function focusTarget(name: string, attempts = 10): void {
  const element = document.querySelector<HTMLElement>(`[data-command-target="${name}"]`);
  if (element) {
    element.focus();
    if (element instanceof HTMLInputElement) element.select();
    return;
  }
  if (attempts > 0) requestAnimationFrame(() => focusTarget(name, attempts - 1));
}
