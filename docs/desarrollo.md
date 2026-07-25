# Desarrollo

## Requisitos

- macOS
- Python 3.12
- Node 20 o superior

## Puesta en marcha

```bash
make install     # dependencias de Python y de la interfaz
make dev         # compila la interfaz si falta y abre la aplicación
```

## Trabajar en la interfaz

Para tener recarga en caliente, en dos terminales:

```bash
make api                      # backend en http://127.0.0.1:8765, con reload
cd web && npm run dev         # interfaz en http://127.0.0.1:5173
```

Vite redirige `/api` al backend. La única diferencia con la aplicación real es que en el navegador
no existe el puente nativo: donde deberían aparecer los diálogos de archivo de macOS, la pantalla
de bienvenida muestra un campo de texto para escribir la ruta a mano.

## Verificar

```bash
make check       # lint (ruff + tsc) y tests; es lo mismo que corre CI
make test
make lint
```

Los tests usan bases de datos temporales y una carpeta de ajustes aislada mediante la variable
`SIGMA_SETTINGS_DIR`. Nunca tocan tu base real.

## Empaquetar

```bash
make app         # → dist/Sigma.app
```

El script compila la interfaz, genera el icono `.icns` desde `web/public/logo.png` y llama a
PyInstaller con `Sigma.spec`.

**Constrúyelo en un entorno virtual limpio.** PyInstaller recorre todo lo que sea importable, así
que si tu entorno tiene numpy, Jupyter o similares, se van al bundle. `Sigma.spec` los excluye
explícitamente por eso mismo; si aparece una dependencia pesada nueva, agrégala a `EXCLUDES`.

## Estructura de los tests

| Archivo | Qué cubre |
|---|---|
| `test_accounts.py` | Crear, editar, renombrar y eliminar cuentas |
| `test_movements.py` | Gastos, ingresos, transferencias, saldos y listados |
| `test_reconciliations.py` | El ciclo de conciliación |
| `test_schema.py` | Creación del esquema y migración desde el formato anterior |
| `test_settings.py` | Ajustes de la aplicación y recientes |
| `test_database_file.py` | Abrir, crear, respaldar, restaurar y bloquear el archivo |
| `test_preferences.py` | Preferencias guardadas dentro del `.db` |
| `test_api.py` | Todas las rutas HTTP, con `TestClient` |

Las fixtures compartidas (`db`, `wallet`, `card`) están en `tests/conftest.py`.

## Publicar una versión

1. Subir la versión en `pyproject.toml`, `src/sigma/__init__.py` y `Sigma.spec`.
2. Cerrar la sección `[Unreleased]` del `CHANGELOG.md` con la fecha.
3. `make check && make app`.
4. Probar `dist/Sigma.app` abriéndola desde `/Applications`.
5. Etiquetar (`git tag v1.0.0`) y adjuntar el `.app` comprimido a la release de GitHub.

No hay publicación automática: la aplicación no se distribuye por PyPI ni por ningún índice.
