# Interfaz

Este documento describe el sistema de diseño **que el proyecto usa realmente**. Si cambias algo
aquí, cámbialo también en `web/src/styles.css`.

## Principios

**Registrar es lo importante.** El formulario de registro está siempre visible en Resumen, nunca
detrás de un botón. Necesita dos campos para funcionar: monto y descripción. Todo lo demás tiene
un valor por defecto razonable.

**Lenguaje llano.** "Gasto", "Saldo disponible", "Conciliar". Nada de "Verification Node",
"Chronological Activity" ni "Ledger". Si una etiqueta necesita explicación, está mal escrita.

**Verde y rojo son el signo del dinero.** Nunca se usan para botones, estados, validaciones ni
decoración. Un número verde siempre significa que entra plata; uno rojo, que sale. Para llamar la
atención está el acento; para advertir, `--caution`.

**Todo monto pasa por `<Money>`.** Ese componente es el único que decide formato y color, y da por
hecho que el monto está en pesos chilenos. Nunca formatees un peso a mano en un componente.

En Inversiones, donde un monto puede estar genuinamente en dólares (el precio de un ticker, un
dividendo pagado en USD), se usa `<CurrencyMoney amount currency>` en su lugar — mismo criterio de
color, formato distinto según la moneda. Todo lo que ya está convertido a pesos por el backend
(valor de mercado, ganancia, patrimonio total) sigue pasando por `<Money>` normal.

**Densidad pareja.** Las filas de listas miden lo mismo en todas las pantallas. Las cifras van
alineadas a la derecha y con `tnum` para que las columnas cuadren.

## Tokens

Definidos en `web/src/styles.css`. Se usan a través de las utilidades de Tailwind
(`bg-surface`, `text-text-muted`, `border-line`…), nunca con valores literales.

| Token | Para qué |
|---|---|
| `--canvas` | Fondo de la ventana |
| `--surface` / `--surface-hover` | Tarjetas y su estado al pasar el cursor |
| `--line` / `--line-strong` | Bordes de un pelo, y su versión de énfasis |
| `--text` / `--text-muted` / `--text-subtle` | Los tres niveles de texto, y son suficientes |
| `--accent` / `--accent-soft` | La única acción destacada por pantalla |
| `--positive` / `--negative` | Exclusivamente el signo del dinero |
| `--caution` | Advertencias (bloqueo del archivo, pendiente de conciliar) |

Hay tema oscuro y claro; el oscuro es el que viene por defecto. El tema se aplica con
`data-theme` en `<html>` y se guarda en los ajustes de la aplicación.

## Tipografía

Fuentes del sistema, a propósito: la aplicación funciona sin conexión dentro de su propia
ventana, así que pedir una fuente web solo puede ser una demora o un error. San Francisco ya trae
cifras tabulares, que es lo único que la app necesita de una tipografía.

Tamaños: 20px para el título de una pantalla, 14px para el cuerpo, 13px para filas de datos, 11px
para etiquetas y notas al pie. No hay más.

## Componentes

`web/src/components/` — `Button`, `Card` + `SectionHeader` + `PageHeader`, `Field` (con `Input`,
`AmountInput`, `Select`, `Checkbox`, `Segmented`), `Modal`, `Money`, `ActivityList`, `EmptyState`,
`Sidebar`, `Toaster`.

Antes de escribir una pieza nueva, revisa si alguna de esas ya sirve. `ActivityList` en
particular es el único lugar donde se dibuja un movimiento, y lo usan tanto Resumen como
Movimientos.

## Errores

Un error de un campo se muestra **junto al campo**, no como notificación flotante. Las
notificaciones (`Toaster`) son para confirmar algo que ya pasó o para avisar de una falla que
ocurrió en otra parte de la pantalla.

El texto del error viene del backend y ya está escrito en español para la persona. No lo
reemplaces por uno genérico.

## Accesibilidad

- Cada control tiene `id` y su `<label>` asociado, o un `aria-label`.
- El foco se ve: hay un `:focus-visible` global con el color de acento.
- Los diálogos se cierran con Escape y mueven el foco a su interior al abrirse.
- Se respeta `prefers-reduced-motion`.

## Movimiento

Tres animaciones, y ninguna dura más de 280 ms: `rise` para el contenido de una pantalla, `fade`
para el fondo de un diálogo, `pop` para el diálogo. Las transiciones de hover son de 150 ms.
