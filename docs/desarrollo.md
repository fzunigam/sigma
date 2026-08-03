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

**El bundle sale solo para la arquitectura donde se construye.** PyInstaller no arma binarios
universales aquí, así que compilar en un Mac con Apple Silicon produce una app que no abre en un
Mac Intel. La release se construye en un runner Apple Silicon y el archivo publicado se llama
`Sigma-AppleSilicon.app.zip` para que se note antes de descargarlo.

## Firma y Gatekeeper

Sigma no está firmada con una cuenta de desarrollador de Apple ni notarizada. PyInstaller le pone
una firma *ad-hoc*, que es lo mejor disponible sin pagar la cuenta, y tiene dos consecuencias:

- Quien la descargue verá un aviso la primera vez y tendrá que aprobarla en **Ajustes del Sistema
  → Privacidad y seguridad → Abrir de todos modos**. El atajo de clic derecho → *Abrir* dejó de
  funcionar en macOS Sequoia; las instrucciones del README y de las notas de release ya no lo
  mencionan.
- Si el sello de la firma se rompe, macOS dice que la app **está dañada** y no ofrece ninguna
  salida. Por eso la release verifica con `codesign --verify --deep --strict` dos veces: sobre
  `dist/Sigma.app` recién construida y sobre una copia extraída del zip que va a publicar. El
  archivo se comprime con `ditto`, no con `zip`, porque `zip` aplana los enlaces simbólicos del
  bundle y rompe justamente ese sello.

Para probar el aviso como lo ve quien descarga, marca una copia con la cuarentena a mano:

```bash
xattr -w com.apple.quarantine "0081;00000000;Safari;" /Applications/Sigma.app
```

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
| `test_investments.py` | Compra, venta, dividendo, cambio de moneda, costo promedio y su caché de precios |
| `test_investment_metrics.py` | Ganancia, XIRR, asignación e historial de valor de una cuenta de inversión |
| `test_prices.py` | `sigma/prices.py`, con Yahoo Finance siempre simulado |
| `test_api_investments.py` | Las rutas HTTP de Inversiones, con `TestClient` |

Las fixtures compartidas (`db`, `wallet`, `card`, `fintual`, `client`, `api`) están en
`tests/conftest.py`.

## Publicar una versión

1. Subir la versión en `pyproject.toml` y en `src/sigma/__init__.py`. `Sigma.spec` la lee de ahí,
   no hay que tocarlo.
2. Cerrar la sección `[Unreleased]` del `CHANGELOG.md` con la fecha.
3. `make check && make app`.
4. Probar `dist/Sigma.app` abriéndola desde `/Applications`.
5. Etiquetar y empujar: `git tag v1.0.0 && git push origin v1.0.0`.

El resto lo hace `.github/workflows/release.yml`: construye la app, verifica su firma, la comprime
y crea la release de GitHub con `Sigma-AppleSilicon.app.zip` adjunto. No hay que subir nada a
mano, y la aplicación no se distribuye por PyPI ni por ningún índice.
