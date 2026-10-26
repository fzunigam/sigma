# MEMORY — Sigma

Memoria entre sesiones de desarrollo. La mantiene **Claude**, no se edita a mano. Cada entrada
lleva **fecha absoluta** y va en la sección que corresponde. Un hook global la inyecta al iniciar
sesión y, la primera vez que Claude va a cerrar, le pide revisar si hay algo nuevo que anotar.

**Qué va aquí y qué no.** Solo lo que no vive en otro lugar: preferencias, correcciones, patrones
de trabajo y decisiones del tipo "no volver a proponer". Lo que ya está en `AGENTS.md`, `docs/`,
`CHANGELOG.md` o el historial de git **no se duplica**: se actualiza en su documento. **El repo
es público:** nada de saldos, nombres de cuentas reales ni rutas personales. Cuando pase de ~40
entradas, reorganizar (agrupar, archivar lo viejo).

## Preferences
<!-- Cómo le gusta trabajar al usuario: formato, tono, herramientas -->
- 2026-10-26 — **Cambios visuales: mostrar antes de commitear.** Antes de hacer commit/tag de una
  versión con cambios de interfaz, el usuario quiere ver capturas y aprobar. Preparar todo
  (código, docs, changelog), mostrar, y recién con su visto bueno subir versión y commitear.
- 2026-10-26 — **Para decisiones de diseño, prefiere ver opciones dibujadas** (lienzo con
  variantes lado a lado) antes que descripciones.

## Corrections
<!-- Errores que ya me corrigieron. No repetirlos. -->

## Patterns
<!-- Patrones técnicos y de trabajo que se repiten -->
- 2026-10-26 — **Quitar una función ya publicada exige una migración, no un revert.** El archivo
  del usuario queda en el `schema_version` de la versión más nueva que lo abrió, y el código viejo
  lo rechaza ("versión más nueva"). Se sube `SCHEMA_VERSION` con un paso que deshace el anterior;
  el paso viejo queda vacío para los archivos que nunca lo tuvieron. Probar siempre contra una
  **copia** de la base real (en el scratchpad), nunca contra el original.
- 2026-10-26 — **`rtk find` no acepta `-exec`, `-not` ni predicados compuestos.** Usar
  `/usr/bin/find` directo para eso.
- 2026-10-26 — **`CLAUDE.md` es un symlink a `AGENTS.md`**: las ediciones van a `AGENTS.md`.
- 2026-10-26 — **Capturas de la app sin tocar la base real:** lanzar
  `dist/Sigma.app/Contents/MacOS/Sigma` con `SIGMA_SETTINGS_DIR` en el scratchpad, crear una
  base demo por la API y capturar con Chrome headless (`--screenshot`) contra el puerto que
  muestra `lsof`. `screencapture` falla: la terminal no tiene permiso de grabar pantalla.
- 2026-10-26 — **Verificar cambios de la ventana nativa (AppKit) sin capturas:** un script en el
  scratchpad que envuelve `webview.start`, espera unos segundos y, vía `AppHelper.callAfter`,
  inspecciona `window.native` (styleMask, `hitTest_` sobre el marco) y luego hace `destroy()`.
  Ojo: pywebview pone el WKWebView como content view recién al terminar la primera carga
  (evento `loaded`), así que lo que se agregue antes queda tapado.

## Decisions
<!-- Decisiones tomadas + el porqué, con fecha -->
- 2026-10-26 — **Se retiran las inversiones** (salieron en 1.3.0; no resultaron como se
  esperaba). Detalle en `docs/decisiones/0006-retirar-inversiones.md`. El trabajo sin publicar
  quedó en la rama `archive/inversiones-wip`. No volver a proponer multi-moneda ni inversiones
  salvo que el usuario lo pida.
