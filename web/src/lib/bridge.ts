/**
 * Access to the native macOS file dialogs exposed by `sigma/bridge.py`.
 *
 * pywebview injects `window.pywebview.api` shortly after the page loads, so
 * calls wait for it rather than assuming it is already there. In the browser
 * during `npm run dev` there is no bridge at all; `isAvailable` lets the
 * interface offer a plain text field instead of a dead button.
 */

interface PywebviewApi {
  choose_database(): Promise<{ path: string | null }>;
  choose_new_database(): Promise<{ path: string | null }>;
  reveal(path: string): Promise<{ ok: boolean }>;
  open_releases(): Promise<{ ok: boolean }>;
  quit(): Promise<{ ok: boolean }>;
}

declare global {
  interface Window {
    pywebview?: { api?: PywebviewApi };
  }
}

const READY_TIMEOUT_MS = 3000;

function api(): PywebviewApi | null {
  return window.pywebview?.api ?? null;
}

export function isAvailable(): boolean {
  return api() !== null;
}

async function waitForBridge(): Promise<PywebviewApi | null> {
  const deadline = Date.now() + READY_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const bridge = api();
    if (bridge) return bridge;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  return null;
}

/** Ask for an existing database file. Resolves to `null` if cancelled. */
export async function chooseDatabase(): Promise<string | null> {
  const bridge = await waitForBridge();
  if (!bridge) return null;
  return (await bridge.choose_database()).path;
}

/** Ask where to put a new database file. Resolves to `null` if cancelled. */
export async function chooseNewDatabase(): Promise<string | null> {
  const bridge = await waitForBridge();
  if (!bridge) return null;
  return (await bridge.choose_new_database()).path;
}

export async function revealInFinder(path: string): Promise<void> {
  const bridge = api();
  if (bridge) await bridge.reveal(path);
}

/**
 * Close the app. Used after an update is staged: the script that replaces the
 * bundle is waiting for this process to exit, and reopens Sigma afterwards.
 */
export async function quit(): Promise<void> {
  const bridge = api();
  if (bridge) await bridge.quit();
}

/**
 * Show the downloads page in the browser. Inside the app window it has to be
 * the native `open`: navigating there would replace the interface with a web
 * page and there is no back button. `window.open` is the fallback for
 * `npm run dev`, where there is no bridge.
 */
export async function openReleases(url: string): Promise<void> {
  const bridge = api();
  if (bridge) {
    await bridge.open_releases();
    return;
  }
  window.open(url, '_blank', 'noopener');
}
