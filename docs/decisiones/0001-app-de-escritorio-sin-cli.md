# 0001 — Una aplicación de escritorio, sin línea de comandos

**Estado:** aceptada · 2026-07-24

## Contexto

Sigma nació como herramienta de terminal y fue creciendo: 21 comandos, menús interactivos con
captura de teclas cruda, un bot de Telegram, un servidor web, un dashboard en Next.js, una
aplicación macOS, un instalador de symlinks, un actualizador y respaldos en ZIP.

El resultado medible: `cli.py` tenía 1.394 líneas, el dashboard entero vivía en un componente de
1.777 líneas, y 22 de los 24 archivos de test probaban comandos de terminal. El resultado
cualitativo: registrar un gasto —lo único que la herramienta hace todos los días— dejó de ser
rápido, porque la aplicación había dejado de ser simple.

Además, mantener la CLI y la interfaz gráfica en paralelo significaba escribir cada función dos
veces, con dos conjuntos de errores y dos formas de resolver la cuenta por defecto.

## Decisión

La aplicación de escritorio es el único producto. Se elimina por completo:

- La interfaz de línea de comandos y su empaquetado en PyPI.
- El symlink automático a `/usr/local/bin/sgm`.
- El comando `update` y el aviso de nueva versión.
- Los respaldos en ZIP con CSVs, reemplazados por el archivo `.db` elegible más los respaldos
  automáticos con fecha.
- Las dependencias `typer` y `rich`.

El paquete pasa de `sgm` a `sigma`, porque `sgm` era el nombre del ejecutable de terminal.

## Consecuencias

- Una sola forma de hacer cada cosa, un solo lugar donde arreglarla.
- Se pierde la posibilidad de automatizar con scripts. Es un costo asumido: es una aplicación
  personal, no una herramienta para encadenar en un pipeline.
- La API HTTP local sigue existiendo y sigue siendo un punto de extensión si algún día hiciera
  falta automatizar algo.
- Los 22 tests de la CLI se reemplazan por tests de la capa de datos y de la API, que es donde
  vive el comportamiento que importa.
