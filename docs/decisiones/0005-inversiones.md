# 0005 — Inversiones: acciones y ETFs dentro de Sigma

**Estado:** aceptada · 2026-08-03

## Contexto

Se pidió un módulo de seguimiento de inversiones (acciones y ETFs), al estilo Portfolio
Performance, integrado de verdad con las cuentas y traspasos que ya existen — no un rincón
aislado. Eso significa poder transferir desde la Cuenta Corriente a una cuenta de administradora
(ej. Fintual), que a su vez tiene cash en pesos **y** en dólares además de posiciones con ticker.

Esto choca con dos cosas que hasta ahora eran ciertas en todo Sigma:

1. **"Fuera de alcance: multi-moneda."** Una cuenta de inversión necesita dos monedas a la vez.
2. **"Los saldos se actualizan al escribir, nunca se recalculan al leer."** El valor de una
   cartera cambia solo porque el precio de mercado se movió, sin que el usuario haya escrito nada.

## Decisión

### Multi-moneda, acotada a este módulo

Se rompe la premisa de multi-moneda, pero **solo para cuentas `kind = 'investment'`**. El resto de
Sigma —cuentas de saldo, tarjetas, movimientos, traspasos— sigue siendo enteros en pesos chilenos,
sin excepción. `docs/interfaz.md` y este documento son la referencia de cuándo aplica cada regla.

### La cuenta de inversión vive en `accounts`

`accounts.kind` gana un tercer valor. Su `balance` sigue significando exactamente lo mismo que en
una cuenta `debit`: cash en CLP, movido por traspasos comunes, sin tocar `sigma/db/transfers.py`.
Todo lo nuevo —cash en USD, tenencias, sus transacciones, el caché de precios y tipo de cambio, y
el historial diario de valor— vive en tablas satélite propias, enlazadas por `account_id`. El
detalle está en `base-de-datos.md`.

La alternativa —una tabla `investment_accounts` completamente aparte— se descartó porque transferir
desde la Cuenta Corriente dejaría de ser el mismo traspaso de siempre: la FK de `transfers` apunta
a `accounts`, así que una tabla aparte habría exigido inventar un segundo concepto de "aporte",
justo lo que el pedido original quería evitar.

### El valor de mercado se calcula al leer, con el último precio en caché

Es la excepción explícita al invariante de "el saldo se actualiza al escribir". Nunca se dispara
una llamada de red desde `/api/summary` ni desde Cuentas: siempre se usa el precio que ya está en
`security_prices`/`fx_rates`, así que Resumen sigue siendo instantáneo y funciona sin conexión,
como el resto de la aplicación.

### Precios: sin la librería `yfinance`

Se pidió explícitamente `yfinance`, pero esa librería trae `pandas` y `numpy` — justo lo que la
1.0 sacó del bundle de macOS a propósito (ver el CHANGELOG de esa versión). En vez de eso,
`sigma/prices.py` llama directo al endpoint público de gráficos de Yahoo Finance
(`query1.finance.yahoo.com/v8/finance/chart/{symbol}`, la misma ruta que `yfinance` envuelve por
dentro) usando `urllib.request` y el contexto SSL de `certifi`, exactamente el patrón que ya usa
`sigma/updates.py` para el chequeo de versión. Cero dependencias nuevas, y el mismo criterio de
"cualquier falla se trata como silencio, nunca como error": sin internet, el último precio en
caché se queda donde estaba.

Precios se refrescan **solo** al abrir la sección Inversiones — nunca en segundo plano, nunca
bloqueando el arranque.

### Costo promedio, y una excepción al patrón de editar/borrar

Comprar y vender usan costo promedio, no FIFO. La complicación: a diferencia de `accounts.balance`
(una suma lineal, donde editar un movimiento antiguo es "revertir el delta viejo y aplicar el
nuevo"), el costo promedio depende del **orden** de las transacciones. Editar o borrar una compra
antigua de un ticker puede cambiar la ganancia que registró una venta posterior de ese mismo
ticker.

La solución: `sigma.db.investments.recompute_holding` no aplica un delta — recalcula la tenencia
completa desde cero, reproduciendo en orden todas las compras y ventas no borradas de esa cuenta y
ese ticker, y de paso vuelve a escribir la ganancia realizada de cada venta. Es más trabajo que un
delta, pero la lista de transacciones de un ticker es corta, así que el costo es insignificante, y
es la única forma de que los números sigan siendo correctos después de una corrección.

### La rentabilidad (IRR) se mide con traspasos, no con compras y ventas

El flujo de caja que alimenta el XIRR de una cuenta de inversión son los **traspasos** hacia y
desde ella, no sus compras, ventas o dividendos. Una compra solo cambia cash por una tenencia de
igual valor; un dividendo agrega cash que el valor final ya refleja; una venta hace lo inverso de
una compra. Nada de eso es plata entrando o saliendo de la inversión — es la misma plata
reacomodándose adentro. Lo único que sí lo es son los traspasos que cruzan el borde de la cuenta.

## Alternativas descartadas

**Tabla de cuentas de inversión completamente separada.** Ver más arriba — rompe el traspaso
como gesto único.

**Cotizar acciones y fondos mutuos (Fintual) por igual.** Se descartó para esta versión: Fintual
no tiene ticker bursátil ni API pública, así que su valor tendría que actualizarse a mano y con una
lógica de valorización distinta a la de un ticker. Queda fuera del alcance hasta que valga la pena
resolverlo aparte.

**Cambio de moneda bidireccional (USD → CLP).** Se implementó solo CLP → USD, que es el caso real
pedido (fondear una compra en dólares). Guardar la dirección inversa es una columna más el día
que haga falta retirar dólares invertidos de vuelta a pesos.

## Consecuencias

- `AGENTS.md`/`CLAUDE.md` deja de decir "multi-moneda" en su lista de fuera de alcance sin
  calificar; ahora apunta aquí.
- Un archivo de Sigma anterior a esta versión se actualiza solo al abrirlo (`UPGRADES[3]` en
  `sigma/db/schema.py`), con el respaldo automático de siempre antes de tocar nada.
- Todo el módulo se probó con `sigma.prices.fetch_quote` siempre simulado (`monkeypatch`) en los
  tests — la suite sigue sin tocar la red.
