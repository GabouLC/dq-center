# 0011 · Inicio de sesión con correo y contraseña propio

**Estado:** aceptada (2026-10-15). Ajusta el ADR-07 del Documento de Arquitectura
y reemplaza el modo demo con selección de rol.

## Contexto

El portal entraba eligiendo un rol de demostración, sin credenciales: servía para
probar los permisos, pero no para la HU-13, que pide controlar quién accede. El
documento propone Firebase Authentication con Google, que depende de configurar la
consola de Firebase y de que cada usuario tenga una cuenta de Google. El portal
también debe funcionar en local y en el sandbox, sin servicios externos.

## Decisión

La API emite sus propias sesiones a partir de un correo y una contraseña
(`dqc.api.autenticacion`):

- **Contraseñas.** Se guardan como PBKDF2-SHA256 (600 000 iteraciones, sal de 16 bytes),
  nunca en claro, en `credenciales/{email}` (Firestore) o en `data/config_local.json`.
  Las reglas siguen NIST 800-63B: largo mínimo de 10, sin el usuario y sin repeticiones,
  en vez de exigir símbolos.
- **Sesión.** Token `dqs1.<datos>.<firma>` firmado con HMAC-SHA256 que vence a las
  8 horas. Lleva un sello de la contraseña vigente: cambiarla, restablecerla o quitar el
  acceso invalida las sesiones abiertas sin guardar una lista de sesiones. El secreto sale
  de `DQC_SECRETO` (Secret Manager en Cloud Run) y la API no arranca en Cloud Run sin él.
- **Acceso cerrado por defecto.** Solo entra una cuenta con rol. Correo inexistente,
  contraseña equivocada y cuenta sin rol devuelven el mismo 401, y una cuenta inexistente
  cuesta el mismo cálculo PBKDF2, así que la respuesta no revela qué correos existen.
- **Bloqueo.** Cinco intentos fallidos seguidos bloquean la cuenta 15 minutos (423). El intento
  se cuenta antes de verificar la contraseña, así que varios en paralelo no pasan el límite; un
  correo que no existe se bloquea igual, para que el bloqueo tampoco revele qué cuentas hay; y
  equivocar la contraseña actual al cambiarla también cuenta. En Firestore la credencial se lee
  sin caché, para que un cambio o un bloqueo valga al instante en todas las instancias.
- **Altas y olvidos.** El administrador da acceso y recibe una contraseña temporal de un
  solo uso; con ella solo se puede cambiar la contraseña. Cada inicio, intento fallido,
  bloqueo, cambio y restablecimiento queda en la auditoría.

Google vía Firebase queda como opción adicional (`DQC_AUTH=firebase`); la API acepta
ambos tipos de token.

## Consecuencias

- La HU-13 se cumple sin depender de la consola de Firebase ni de cuentas de Google.
- La API custodia hashes de contraseñas: la colección `credenciales` no se expone por
  ningún endpoint, y Firestore la protege con IAM.
- No hay recuperación por correo: un olvido lo resuelve un administrador. Es aceptable para
  un portal interno con pocos usuarios.
- En local, las cuentas `*@demo.local` entran con `DQC_CLAVE_DEMO` (por defecto
  `SmartDQ-2026`). Ese atajo está prohibido en Cloud Run: la API no arranca si se activa ahí.
