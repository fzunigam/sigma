# Base de datos

## El archivo

Todos tus datos están en un archivo `.db` que eliges tú. La aplicación recuerda cuál es en
`~/Library/Application Support/Sigma/settings.json`, junto con los últimos cinco usados y el tema.

Las **cuentas por defecto** no se guardan ahí sino dentro del propio `.db`, en la tabla `meta`.
Así, si copias el archivo a otro computador, se lleva su configuración puesta.

## Guardarlo en Google Drive

Es el uso previsto: eliges un archivo dentro de la carpeta local de Drive y el servicio lo
sincroniza solo. Pero SQLite en una carpeta sincronizada tiene un riesgo real —el cliente de
sincronización puede subir el archivo mientras se está escribiendo— así que Sigma toma cuatro
medidas, todas en `sigma/db/connection.py`:

**Sin WAL.** El modo por defecto de SQLite deja archivos `-wal` y `-shm` al lado de la base.
Drive los sincroniza por separado y fuera de orden, y una base sin su WAL correspondiente queda
inconsistente. Sigma usa `journal_mode = DELETE`, que no deja nada al lado.

**`synchronous = FULL`.** Cada escritura llega al disco antes de que la operación termine, así
el cliente de sincronización nunca ve un estado a medias.

**Conexiones cortas.** Se abre una conexión por operación y se cierra enseguida. La ventana en
que el archivo está ocupado dura milisegundos.

**Respaldo antes de abrir.** Ver más abajo.

Aun así, la regla de oro es la de siempre: **no tengas Sigma abierto en dos computadores a la
vez.** Para eso está el aviso de bloqueo.

## Respaldos automáticos

Sigma guarda una copia en `.sigma-backups/`, dentro de la misma carpeta, con la fecha y hora en el
nombre. Se conservan las últimas 10.

Se hace en dos momentos:

- **Al abrir la aplicación**, como máximo una vez al día. Sin el límite, abrir Sigma diez veces en
  una tarde borraría diez días de historial.
- **Al elegir un archivo en el diálogo** (abrir otra base, restaurar), siempre. Es una acción
  deliberada y conviene tener el punto de retorno exacto.

La copia se hace con la API de respaldo de SQLite, no con `cp`, así que es consistente aunque algo
más esté escribiendo en ese momento.

Se restauran desde **Ajustes → Respaldos automáticos**. Antes de reemplazar la base activa, Sigma
respalda el estado actual, así que restaurar también se puede deshacer.

## Aviso de bloqueo

Al abrir una base, Sigma escribe un archivo `<nombre>.db.lock` con el nombre del equipo y el
número de proceso. Si al abrir encuentra un bloqueo de **otro** equipo, muestra una advertencia en
Ajustes.

Es un aviso, no un candado: una carpeta sincronizada no permite bloqueo real. Un bloqueo dejado
por un cierre forzado en este mismo computador se detecta como obsoleto (el proceso ya no existe)
y se ignora, para que un cierre brusco no deje una advertencia permanente.

## Esquema

```sql
accounts(
    id TEXT PK, name, kind CHECK (kind IN ('debit','credit','investment')),
    balance INT, credit_limit INT, created_at, deleted_at)

movements(
    id TEXT PK, kind CHECK (kind IN ('expense','income')),
    amount INT CHECK (amount > 0), description,
    account_id → accounts, date,
    pending INT DEFAULT 1,
    reconciliation_id → reconciliations NULL,
    created_at, deleted_at)

transfers(
    id TEXT PK, from_account → accounts, to_account → accounts,
    amount INT CHECK (amount > 0), description DEFAULT '',
    date, created_at, deleted_at)

reconciliations(
    id TEXT PK, net_amount INT, movement_count INT, date, created_at)

meta(key TEXT PK, value TEXT)

-- Inversiones: ver la sección propia más abajo.
investment_cash_usd(account_id → accounts PK, balance INT)

investment_holdings(
    account_id → accounts, ticker,
    quantity REAL, avg_cost REAL, currency,
    PK (account_id, ticker))

investment_transactions(
    id TEXT PK, account_id → accounts,
    kind CHECK (kind IN ('buy','sell','dividend','fx_exchange')),
    ticker NULL, quantity REAL NULL, price REAL NULL, fees INT DEFAULT 0,
    currency NULL, clp_amount INT NULL, usd_amount INT NULL, realized_gain INT NULL,
    date, created_at, deleted_at)

security_prices(ticker TEXT PK, name, currency, price REAL, fetched_at)

fx_rates(pair TEXT PK, rate REAL, fetched_at)

investment_value_history(account_id → accounts, date, value_clp INT, PK (account_id, date))
```

### Cómo se leen los saldos

En una cuenta de saldo (`debit`), `balance` es lo que tienes. En una tarjeta (`credit`), `balance`
es lo que **debes**, y `credit_limit` es el máximo. Por eso el signo se invierte: un gasto con la
tarjeta sube `balance`, y pagarla lo baja. La API expone además un campo calculado `available`,
que es el saldo en una y el cupo restante en la otra.

### Fechas

`date` es el día del movimiento, en formato `YYYY-MM-DD`; es lo que ordena y filtra la interfaz.
`created_at` es cuándo se registró, y sirve solo para desempatar dentro de un mismo día.

### La descripción de un traspaso

`transfers.description` guarda solo la nota que escribió la persona, sin la palabra
"Transferencia". Esa palabra la pone la interfaz al mostrar la fila, y la búsqueda la considera
igual, así que buscar *transferencia* encuentra todos los traspasos y buscar *tarjeta* encuentra
el que dice "pago tarjeta".

## Inversiones

Una cuenta `kind = 'investment'` es una fila más en `accounts`: su `balance` es su cash en pesos,
movido por traspasos normales, igual que una cuenta de saldo. Todo lo demás vive en tablas propias,
enlazadas por `account_id`:

- **`investment_cash_usd`** — el cash en dólares, en centavos enteros (mismo criterio de "sin
  decimales que acumulen error" que el resto de la aplicación, adaptado a que el dólar sí los
  tiene).
- **`investment_holdings`** — cuánto se tiene de cada ticker y a qué costo promedio, en la moneda
  nativa del ticker. Es un valor **derivado**: `sigma.db.investments.recompute_holding` lo
  reconstruye desde `investment_transactions` cada vez que una compra o venta de ese ticker se crea,
  edita o borra, porque el costo promedio depende del orden de las transacciones y no se puede
  parchar con un delta como el saldo de una cuenta. Ver
  [decisiones/0005-inversiones.md](decisiones/0005-inversiones.md).
- **`investment_transactions`** — la fuente de verdad: compra, venta, dividendo o cambio de
  moneda. `realized_gain` se recalcula junto con la tenencia, así que una corrección en una compra
  antigua actualiza la ganancia de las ventas posteriores de ese ticker.
- **`security_prices`** / **`fx_rates`** — el caché de precios y del tipo de cambio USD/CLP, la
  única escritura que hace `sigma/prices.py` (Yahoo Finance, sin la librería `yfinance`). El valor
  de una cuenta de inversión y el patrimonio total en Resumen se calculan siempre desde este caché,
  nunca desde una llamada de red en el camino — Resumen sigue siendo instantáneo y funciona sin
  conexión, como el resto de Sigma. El caché se refresca solo al abrir la sección Inversiones.
- **`investment_value_history`** — una foto del valor total de la cuenta por día, para el gráfico
  de evolución. Solo existe desde que la cuenta empieza a usarse; no hay forma de reconstruir el
  pasado.

## Versiones del formato

La tabla `meta` guarda `schema_version`. Al abrir un archivo, Sigma aplica las actualizaciones
pendientes que hay en `UPGRADES`, dentro de `sigma/db/schema.py`, y siempre después de respaldar.
Un archivo escrito por una versión **más nueva** de Sigma se rechaza en vez de abrirse, porque
abrirlo con código antiguo perdería lo que esa versión agregó.

| Versión | Qué cambió |
|---|---|
| 1 | El formato con el que salió Sigma 1.0.0 |
| 2 | `transfers.description` |
| 3 | Cuentas de inversión: `kind = 'investment'`, tenencias, transacciones, caché de precios/tipo de cambio e historial de valor |

## Migración desde la versión anterior

Si existe una base de la versión pre-1.0 en `~/.local/share/sgm/sigma.db`, la pantalla de
bienvenida ofrece traerla. **El archivo original nunca se toca**: se crea uno nuevo donde tú
elijas y se copian los datos.

Qué cambia en el camino:

| Antes | Ahora |
|---|---|
| `accounts.type` | `accounts.kind` |
| tabla `movement_marks` | columna `movements.pending` |
| `movements.created_at` (era la fecha) | `movements.date` |
| `render_history` | `reconciliations` |
| cuenta reservada `deleted` | cuenta normal marcada como eliminada |
| `~/.config/sgm/config.toml` | tabla `meta` del propio `.db` |

Lo único que no sobrevive es el vínculo entre las conciliaciones antiguas y sus movimientos: la
tabla `render_history` guardaba solo un total, sin registrar qué cerraba. Esos movimientos quedan
como ya conciliados pero sin conciliación asociada. De ahora en adelante el vínculo sí se guarda.

La migración está cubierta por `tests/test_schema.py`, que arma una base con el formato antiguo y
verifica saldos, marcas, fechas y borrados.
