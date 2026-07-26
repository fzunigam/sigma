# Arquitectura

## Qué es Sigma

Una aplicación de escritorio para macOS, de un solo usuario, que registra gastos, ingresos y
transferencias entre cuentas propias. Todos los datos viven en un archivo `.db` que el usuario
elige y puede dejar en una carpeta de Google Drive para que quede respaldado.

No hay servidor, no hay cuentas de usuario, no hay red. La aplicación nunca hace una petición
fuera de `127.0.0.1`.

## Las tres piezas

```
┌─────────────────────────────────────────────┐
│  Ventana nativa (pywebview / WKWebView)     │
│  ┌───────────────────────────────────────┐  │
│  │  Interfaz  React + Vite               │  │
│  └───────────────┬───────────────────────┘  │
└──────────────────┼──────────────────────────┘
                   │ HTTP a 127.0.0.1:<puerto libre>
┌──────────────────┼──────────────────────────┐
│  API  FastAPI    ▼                          │
│  ┌───────────────────────────────────────┐  │
│  │  sigma/db/   acceso a datos           │  │
│  └───────────────┬───────────────────────┘  │
└──────────────────┼──────────────────────────┘
                   ▼
            archivo .db elegido
```

`sigma/main.py` levanta el servidor en un hilo, pide un puerto libre al sistema operativo y abre
la ventana apuntando a él. Cuando la ventana se cierra, el proceso termina.

## Por qué un servidor local en vez de llamadas directas

La interfaz corre dentro de un WKWebView, así que necesita hablar HTTP con algo. Un servidor
FastAPI local es la forma más simple de darle acceso a SQLite sin inventar un protocolo propio, y
además permite desarrollar la interfaz en el navegador con recarga en caliente (`make api` +
`npm run dev`).

El costo es un puerto abierto en loopback mientras la aplicación está viva. Se pide libre al
sistema en cada arranque, así que dos ventanas nunca chocan.

## Capas

**`sigma/db/`** — Todo el acceso a datos, un módulo por tema: `accounts`, `movements`,
`transfers`, `reconciliations`, `preferences`. Cada función recibe la ruta del archivo de forma
explícita y abre su propia conexión corta a través de `connection.py`. No hay conexión global ni
ORM. La lista combinada de movimientos y traspasos —la que lee la interfaz— vive en `movements`,
porque es una sola consulta que une ambas tablas.

**`sigma/database.py`** — El ciclo de vida del *archivo*: crear, abrir, migrar, restaurar. Aquí
viven las reglas de seguridad para carpetas sincronizadas, en un solo lugar.

**`sigma/api.py`** — Traduce HTTP a llamadas de `sigma/db/`. No tiene lógica de negocio propia,
salvo resolver la cuenta por defecto cuando la interfaz no manda una.

**`web/src/`** — `lib/` (cliente HTTP, formato, puente nativo), `components/` (piezas
reutilizables) y `views/` (una por pantalla). El estado vive en `App.tsx` y baja por props; no
hay librería de estado porque no hace falta.

## Modelo de datos

Cuatro tablas y un diccionario de configuración. El detalle está en
[base-de-datos.md](base-de-datos.md).

- **accounts** — de saldo (`debit`) o tarjeta de crédito (`credit`, con cupo).
- **movements** — gastos e ingresos. Nacen "pendientes de conciliar".
- **transfers** — plata que se mueve entre cuentas propias; no es gasto ni ingreso.
- **reconciliations** — el cierre de un grupo de movimientos, con el vínculo a cuáles cerró.
- **meta** — versión del esquema y cuentas por defecto.

Los montos son enteros en pesos chilenos. No hay decimales porque el peso no los usa, y los
enteros no acumulan error.

## Invariantes

1. Los saldos se actualizan al escribir el movimiento, no se recalculan al leer.
2. Eliminar un registro revierte exactamente el cambio que hizo al saldo.
3. Nada se borra de verdad: todo lleva `deleted_at`.
4. Un gasto nunca puede dejar una cuenta de saldo en negativo ni pasarse del cupo de una tarjeta.
5. Una conciliación conserva el neto que registró aunque después se editen sus movimientos: es
   una foto de lo que era cierto en ese momento.

## Qué se sacó en la 1.0

La interfaz de línea de comandos (21 comandos), el bot de Telegram, los respaldos en ZIP con
CSVs, el actualizador automático, el symlink a `/usr/local/bin` y la publicación en PyPI. Cada una
de esas piezas agregaba superficie que mantener sin hacer más fácil registrar un gasto.

Ver [decisiones/0001-app-de-escritorio-sin-cli.md](decisiones/0001-app-de-escritorio-sin-cli.md).
