# 0002 — El usuario elige dónde vive el archivo de datos

**Estado:** aceptada · 2026-07-24

## Contexto

Hasta la versión 0.4 la base de datos estaba fija en `~/.local/share/sgm/sigma.db`. Para
respaldarla había que exportar un ZIP con CSVs a mano y guardarlo en alguna parte; para
restaurarla, subir ese ZIP. Nadie hace eso con la frecuencia necesaria.

La forma en que la gente respalda archivos hoy es dejarlos en una carpeta que se sincroniza sola.

## Decisión

La aplicación abre un archivo `.db` que el usuario elige mediante el diálogo nativo de macOS. La
ruta se guarda en los ajustes de la aplicación, con una lista de recientes.

Los respaldos manuales en ZIP se eliminan: son redundantes cuando el archivo está en Drive, que
además guarda su propio historial de versiones.

## El problema de SQLite en carpetas sincronizadas

Es real, y por eso hay contramedidas concretas en `sigma/db/connection.py`:

1. **`journal_mode = DELETE`** en vez de WAL. WAL deja archivos `-wal` y `-shm` al lado de la
   base; los clientes de sincronización los suben por separado y fuera de orden, y una base sin su
   WAL correspondiente queda inconsistente.
2. **`synchronous = FULL`**, para que una escritura esté en disco antes de que la operación
   termine.
3. **Conexiones cortas**, una por operación.
4. **Respaldo con fecha antes de cada apertura**, en `.sigma-backups/`, rotando los últimos 10, y
   hecho con la API de respaldo de SQLite en vez de una copia de archivo.
5. **Aviso de bloqueo** cuando el archivo parece abierto en otro equipo.

## Alternativas descartadas

**Trabajar sobre una copia local y sincronizar a la carpeta elegida.** Elimina el riesgo por
completo, pero deja dos archivos y un modelo mental confuso: ¿cuál es el bueno? ¿Qué pasa si se
desincronizan? Se prefirió la vía directa con protecciones.

**Sincronización propia.** Requeriría un servidor, y con eso cuentas, autenticación y datos
financieros personales en manos de alguien más. Está fuera de alcance a propósito.

## Consecuencias

- Respaldar deja de ser una tarea: es dónde guardas el archivo.
- Se puede tener más de una base (personal, hogar) y cambiar entre ellas desde Ajustes.
- El bloqueo es un aviso, no un candado: dos equipos escribiendo a la vez siguen pudiendo perder
  cambios. Se mitiga avisando, no impidiendo.
