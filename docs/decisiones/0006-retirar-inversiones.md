# 0006 — Se retiran las inversiones

**Estado:** aceptada · 2026-10-26

Revierte [0005](0005-inversiones.md).

## Contexto

La 1.3.0 agregó la sección Inversiones: cuentas con cash en pesos y dólares, posiciones, precios
en vivo y métricas de cartera. En el uso real no resultó como se esperaba, y una sección que no se
usa a gusto es justo lo que la regla principal de Sigma pide sacar.

## Decisión

Sigma vuelve a ser lo que era en la 1.2: cuentas de débito y tarjetas de crédito, todo en pesos
enteros. Se elimina la sección, sus rutas, sus tablas y la consulta de precios por internet.

El formato del archivo pasa a la versión 4, que deshace la 3:

- Se borran las tablas de inversiones (`investment_*`, `security_prices`, `fx_rates`).
- Cada cuenta `investment` pasa a `debit`, para no romper las transferencias que la nombren. Si
  su saldo en pesos es 0 queda archivada; si tiene pesos, sigue visible para que nada desaparezca
  de los totales sin aviso.
- La tabla `accounts` se reconstruye con el `CHECK` original (`'debit', 'credit'`).

Lo que se pierde al migrar (posiciones, transacciones, caja en dólares) queda en el respaldo que
Sigma hace siempre antes de actualizar el formato.

## Consecuencias

- Multi-moneda vuelve a estar fuera de alcance, sin excepción.
- El trabajo en curso que extendía la multi-moneda al resto de las cuentas quedó guardado en la
  rama `archive/inversiones-wip`, sin publicar. Si se retoma la idea, se parte de una propuesta
  nueva, no de esa rama tal cual.
