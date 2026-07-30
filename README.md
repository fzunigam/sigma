# Sigma

Registro simple de finanzas personales para macOS.

Sigma es una aplicación de escritorio para anotar en qué se te va la plata, sin cuentas, sin
suscripción y sin conexión a internet. Todos tus datos viven en un solo archivo que tú eliges: si
lo guardas en tu carpeta de Google Drive, queda respaldado solo.

## Instalación

Necesitas un Mac con Apple Silicon (M1 o posterior).

1. Descarga `Sigma-AppleSilicon.app.zip` desde
   [Releases](https://github.com/fzunigam/sigma/releases).
2. Descomprime con doble clic y arrastra **Sigma** a tu carpeta `Aplicaciones`.
3. Ábrela. La primera vez macOS la bloquea; abajo está cómo pasar ese aviso.

### La primera vez macOS la bloquea

Sigma no está firmada con una cuenta de desarrollador de Apple, así que el sistema avisa que no
puede comprobar quién la hizo. Para abrirla igual:

1. Haz doble clic en **Sigma** y cierra el aviso que aparece.
2. Abre el menú Apple → **Ajustes del Sistema** → **Privacidad y seguridad**.
3. Baja hasta el mensaje sobre Sigma y pulsa **Abrir de todos modos**.

Solo hace falta una vez. Desde entonces se abre con doble clic como cualquier otra aplicación.

El atajo antiguo de clic derecho → *Abrir* ya no sirve: Apple lo quitó en macOS Sequoia.

Si en vez de eso dice que la app **está dañada**, se perdió algo al descomprimir —normalmente
porque el archivo pasó por otra herramienta o se reenvió por mensajería—. Descárgalo de nuevo
desde Releases y descomprímelo con doble clic en Finder. Si aun así insiste, quita la marca de
cuarentena desde la Terminal:

```bash
xattr -dr com.apple.quarantine /Applications/Sigma.app
```

## Primer uso

Al abrirla por primera vez eliges dónde vivirán tus datos:

- **Crear una base de datos nueva** — empezar de cero. Guárdala dentro de tu carpeta de Google
  Drive o Dropbox y el respaldo queda resuelto.
- **Abrir una base existente** — si ya tienes un archivo, por ejemplo en otro computador.
- **Traer datos de la versión anterior** — aparece solo si tenías Sigma instalado antes. Copia tus
  cuentas y movimientos al archivo nuevo sin tocar el original.

Después, crea tus cuentas en **Cuentas** y ya puedes registrar.

## Cómo se usa

**Registrar** es lo primero que ves. Escribes el monto, una descripción y listo. La cuenta, la
fecha y el resto vienen con valores por defecto.

**Cuentas** pueden ser de dos tipos:

- *De saldo* — una cuenta corriente o el efectivo que llevas encima. Muestra cuánto tienes.
- *Tarjeta de crédito* — tiene un cupo. Muestra cuánto has gastado y cuánto te queda disponible.

**Traspasos** mueven plata entre tus propias cuentas —sacar del banco, pagar la tarjeta— y no
cuentan como gasto ni como ingreso. Puedes agregarles una descripción para distinguirlos.

**Conciliar** es para cuadrar. Cada movimiento nace marcado como "por conciliar"; cuando revisas
un grupo y ves que está correcto, presionas *Conciliar* y se guarda un resumen con la fecha y el
resultado neto. Los movimientos dejan de estar pendientes, pero la conciliación conserva el
vínculo, así que siempre puedes volver a ver qué incluyó.

**Movimientos** muestra un mes a la vez, con sus totales de ingresos, gastos y balance. El
buscador de arriba mira en todo tu historial, no solo en el mes que tienes a la vista, y no
distingue mayúsculas ni tildes.

**Corregir** lo que registraste: el lápiz al final de cada fila abre el movimiento para cambiarle
el monto, la descripción, la cuenta o la fecha. Los saldos se ajustan solos. Eliminarlo también se
hace desde ahí.

## Respaldos

Sigma guarda una copia con la fecha en una carpeta `.sigma-backups/` junto a tu archivo: una vez
al día al abrir la aplicación, y siempre que cambies de base o restaures. Se conservan las últimas
10 y se restauran desde **Ajustes**.

Si además tienes el archivo en Drive o Dropbox, cuentas con el historial de versiones de ese
servicio.

> Una advertencia: no dejes Sigma abierto en dos computadores al mismo tiempo sobre el mismo
> archivo. Sigma te avisa si lo detecta, pero la sincronización puede perder cambios.

## Desarrollo

```bash
make install   # dependencias
make dev       # abrir la aplicación
make check     # lint y tests
make app       # construir dist/Sigma.app
```

Los detalles están en [docs/](docs/): [arquitectura](docs/arquitectura.md),
[base de datos](docs/base-de-datos.md), [interfaz](docs/interfaz.md) y
[desarrollo](docs/desarrollo.md).

## Licencia

[MIT](LICENSE).
