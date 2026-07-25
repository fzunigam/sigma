# 0003 — "Conciliación" en vez de "render"

**Estado:** aceptada · 2026-07-24

## Contexto

Las versiones anteriores tenían un ciclo llamado *render*: cada movimiento nacía "marcado", y el
comando `sgm render` sumaba los marcados, guardaba el neto en `render_history` y los desmarcaba.

La mecánica era útil —permite revisar un grupo de movimientos y darlos por cuadrados— pero el
nombre no significaba nada. En la interfaz apareció como "Verification Node", "Pending Marked
Sum" y "Audit Archive", que significan todavía menos.

Además, `render_history` guardaba únicamente un total y una fecha. Los movimientos que cerraba
quedaban simplemente desmarcados, sin ninguna referencia. La información de qué compuso cada
cierre se perdía para siempre en el momento de crearlo.

## Decisión

Se conserva la mecánica y se cambia el nombre a **conciliación**, la palabra que se usa
normalmente en Chile para cuadrar lo registrado con lo real.

En la interfaz:

| Antes | Ahora |
|---|---|
| Mark for render cycle | Incluir en la conciliación |
| Pending Marked Sum | Pendiente de conciliar |
| Render Cycle / Verification Node | Conciliar |
| Audit Archive | Últimas conciliaciones |

En los datos:

- `movement_marks` desaparece como tabla y pasa a ser la columna `movements.pending`.
- `render_history` pasa a ser `reconciliations`, con `movement_count`.
- **Nuevo:** `movements.reconciliation_id` guarda a qué conciliación pertenece cada movimiento.

## Consecuencias

- Cualquier conciliación pasada se puede abrir para ver exactamente qué movimientos cerró.
- Una conciliación conserva el neto que registró aunque después se borre alguno de sus
  movimientos. Es deliberado: es una foto de lo que era cierto en ese momento, y corregir un error
  posterior no debería reescribir la historia.
- Las conciliaciones migradas desde `render_history` no tienen movimientos asociados, porque esa
  información nunca se guardó. Aparecen con `movement_count = 0`.
