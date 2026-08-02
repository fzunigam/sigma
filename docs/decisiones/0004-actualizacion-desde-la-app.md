# 0004 — Sigma se actualiza sola

**Estado:** aceptada · 2026-08-02

Revierte, en parte, un punto de [0001](0001-app-de-escritorio-sin-cli.md): el aviso de versión
nueva vuelve, ahora dentro de la aplicación.

## Contexto

La 1.0 eliminó el actualizador junto con la CLI, y con razón: era un comando de terminal
(`sgm update`) que hacía `pip install --upgrade` sobre un paquete de PyPI que ya no existe.

Pero la aplicación se distribuye como un `.zip` en GitHub Releases, y hasta ahora enterarse de una
versión nueva dependía de ir a mirar la página. Instalarla eran cinco pasos manuales —descargar,
descomprimir, cerrar la aplicación, arrastrar, reemplazar— más el diálogo de Gatekeeper, que
aparece de nuevo con cada versión porque la marca de cuarentena la pone el navegador al descargar.

Sigma la usan personas que no programan. Cinco pasos y un diálogo de seguridad que dice que la
aplicación "no se puede comprobar" es exactamente el tipo de fricción por la que alguien se queda
en una versión vieja para siempre.

## Decisión

La aplicación avisa cuando hay una versión nueva y se actualiza sola tras una confirmación.

**El aviso** (`sigma/updates.py`) consulta la API pública de releases de GitHub. Es la única
petición que Sigma hace fuera de `127.0.0.1`. No manda nada y cualquier falla se reporta como "no
hay novedad": sin conexión la aplicación funciona igual y el aviso simplemente no aparece.

**La instalación** (`sigma/installer.py`) descarga el `.zip` de la release, lo expande con
`ditto`, verifica que la firma valide y que la versión sea la prometida, y recién entonces lanza
un script suelto que espera a que el proceso termine, mueve el bundle viejo a un lado, copia el
nuevo en su lugar y vuelve a abrir Sigma.

Se descarta **Sparkle**, que es lo estándar en macOS, porque significa empotrar un framework de
Objective-C dentro de un bundle de PyInstaller y manejarlo por PyObjC, más generar un appcast en
cada release. Mucho aparato para un botón.

## Consecuencias

- Desaparece el diálogo de Gatekeeper al actualizar: la cuarentena la aplica el navegador, no
  `urllib`, así que un bundle instalado por la propia aplicación no queda marcado. La primera
  instalación sigue igual que siempre.
- El ancla de confianza es TLS contra `github.com`, verificado con el bundle de CA de `certifi`
  que viaja dentro de la aplicación. La aplicación no está firmada con un Developer ID, así que no
  hay firma de Apple que comprobar, y publicar un SHA-256 no agregaría nada: quien controle la
  release controla también el hash.
- Si el `.app` pertenece a otro usuario —se instaló con `sudo`—, Sigma no pide contraseña de
  administrador: avisa y manda a hacerlo a mano. Un camino privilegiado que no se usa para nada
  más no vale lo que cuesta cuidarlo.
- El reemplazo se prueba de verdad: los tests corren el script contra bundles de mentira, con
  `ditto` fallando a propósito, y comprueban que la versión anterior vuelva a su lugar.
- Nada de esto toca la base de datos, que vive fuera de la aplicación, en el archivo que el
  usuario eligió.
