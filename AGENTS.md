# Sigma

Aplicación de escritorio para macOS que registra finanzas personales. Un solo usuario, un solo
archivo de datos, sin servidor ni cuentas en la nube.

**La regla que manda sobre todas las demás: si una función hace que la aplicación sea más difícil
de usar, no va.** Sigma ya fue una herramienta que creció hasta volverse incómoda; la versión 1.0
existe para revertir eso.

## Stack real

| Capa | Qué es |
|---|---|
| Datos | SQLite, montos en pesos enteros, un archivo `.db` que el usuario elige |
| Backend | Python 3.12 + FastAPI, escuchando solo en `127.0.0.1` |
| Ventana | pywebview (WKWebView) |
| Interfaz | Vite + React 18 + TypeScript estricto + Tailwind v4 |
| Empaquetado | PyInstaller → `dist/Sigma.app` |

No hay CLI, no hay paquete en PyPI, no hay build de Windows ni de Linux.

## Estructura

```
src/sigma/
  main.py          Arranque: servidor en un hilo + ventana nativa
  api.py           Rutas HTTP (todo bajo /api)
  database.py      Ciclo de vida del archivo .db: crear, abrir, migrar, restaurar
  settings.py      Ajustes de la app (ruta del .db, recientes, tema)
  bridge.py        Diálogos nativos de archivo expuestos a JavaScript
  db/              Acceso a datos, un módulo por tema
web/src/
  lib/             api, format, bridge, types
  components/      Piezas reutilizables
  views/           Una por pantalla
tests/             pytest, sin dependencias entre archivos
docs/              Ver docs/README.md
```

## Comandos

```bash
make install   # dependencias de Python y de la interfaz
make dev       # abrir la aplicación
make check     # lint + tests (esto es lo que corre CI)
make app       # construir dist/Sigma.app
```

Para trabajar en la interfaz con recarga en caliente: `make api` en una terminal y
`cd web && npm run dev` en otra.

## Reglas de trabajo

**Idioma.** Todo lo que ve el usuario va en español, sin jerga: "Gasto", "Saldo", "Conciliar".
El código, los identificadores, los comentarios y los mensajes de commit van en inglés. La
documentación de `docs/` va en español.

**Mensajes de error.** Los que lanza `sigma.db.errors` se muestran tal cual en la interfaz.
Escríbelos en español, dirigidos a la persona, y di qué hacer: `"Saldo insuficiente en 'Efectivo'.
Disponible: 20000, necesario: 35000."`, no `"insufficient funds"`.

**Base de datos.** El archivo puede estar en una carpeta sincronizada (Drive, Dropbox). Por eso:
sin WAL, conexiones cortas, y respaldo antes de abrir. Todo eso vive en `sigma/db/connection.py`
y no debe eludirse abriendo `sqlite3.connect` por fuera.

**Interfaz.** Sigue `docs/interfaz.md`. Lo importante: verde y rojo son exclusivamente el signo
del dinero, nunca decoración ni estados; todos los montos pasan por el componente `Money`; ningún
archivo debería superar ~300 líneas.

**Tests.** Cada cambio de comportamiento en `sigma/db/` o en `sigma/api.py` necesita un test. La
suite corre en menos de dos segundos; no hay excusa para no ejecutarla.

**Changelog.** Registra los cambios que se notan al usar la aplicación en `CHANGELOG.md`, bajo
`[Unreleased]`, usando Added / Changed / Removed / Fixed. Los refactors internos no van.

**Versiones.** Al publicar una versión (tag `vX.Y.Z` en GitHub): sube `version` en `pyproject.toml`
y `__version__` en `src/sigma/__init__.py`, y mueve `[Unreleased]` del changelog a esa versión con
la fecha del día. Además, **reconstruye e instala la app local** (`make app`, reemplazar
`/Applications/Sigma.app`) para que quede en la misma versión que el tag. `~/Library/Application
Support/Sigma/settings.json` vive fuera del `.app`, así que reinstalar no toca la base de datos
elegida ni el tema — no hay que hacer nada especial para conservarlos.

## Fuera de alcance

Categorías, presupuestos, sincronización propia, otras plataformas y volver a publicar en PyPI. Si
algo de esto parece necesario, discútelo antes de escribir código.

Multi-moneda es fuera de alcance **salvo** en las cuentas de inversión (`kind = 'investment'`),
donde es necesario y está acotado a propósito — ver
[decisiones/0005-inversiones.md](docs/decisiones/0005-inversiones.md). El resto de la aplicación
sigue siendo enteros en pesos chilenos, sin excepción.
