# 0007 — Identidad visual grafito y Σ tipográfica

**Estado:** aceptada · 2026-10-26

## Contexto

El ícono era la letra Σ de una fuente con serifa, negra sobre blanco. Parecía un símbolo
matemático pegado, no una marca; no tenía la forma de cuadrado redondeado que espera macOS, y no
tenía relación con los colores de la app, que vienen en tema oscuro por defecto. Dentro de la
ventana, la barra lateral y la bienvenida mostraban otra cosa: la misma letra sobre el color de
acento.

## Decisión

- **Logo:** una Σ dibujada con contraste (diagonales gruesas, barras finas, remates cortos), en
  un blanco frío sobre un cuadrado redondeado en degradado grafito. Se eligió entre tres variantes
  (doble raya, geométrica y tipográfica); la tipográfica conserva el carácter de la letra pero
  dibujada a propósito.
- **Color:** el grafito del ícono pasa a ser la escala neutra de toda la interfaz (tono 268 en
  OKLCH, en ambos temas). El acento azul se mantiene; verde, rojo y ámbar siguen reservados.
- **Un solo dibujo:** el mismo logo en el Dock, la barra lateral y la bienvenida, dibujado con el
  componente `Logo` dentro de la app y con `assets/logo.svg` como original.

Las reglas de uso están en [interfaz.md](../interfaz.md#identidad-visual).

## Consecuencias

- No hay fuentes web ni lema: el nombre usa la fuente del sistema, como el resto de la interfaz.
- Cambiar el logo exige tocar `assets/logo.svg` y `Logo.tsx` a la vez, y correr `make logo`.
