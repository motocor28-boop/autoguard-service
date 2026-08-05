# Nexo Secure Pro — hoja de ruta

## Hito A: infraestructura reproducible

- Docker Compose con Tuwunel, LiveKit, Redis, PostgreSQL y Caddy.
- TLS obligatorio, federation off, registro por invitación.
- Backups, health checks, límites y registros sin contenido sensible.

## Hito B: Android Alpha

- Aplicación nativa Kotlin/Compose.
- Configuración inicial del servidor.
- Registro mediante invitación.
- Gestión de sesión y dispositivos.
- Lista privada de contactos autorizados.
- Mensajes 1:1 y sincronización offline.

## Hito C: medios

- Notas de voz cifradas.
- Archivos y fotografías cifrados.
- Llamadas de voz 1:1 con LiveKit.
- Reconexión al cambiar entre Wi-Fi y datos móviles.

## Hito D: administración

- Panel web con usuarios, invitaciones, dispositivos y revocación.
- Políticas de mensajes temporales.
- Auditoría administrativa sin registrar contenido de conversaciones.
- Alertas de abuso y límites de intentos.

## Hito E: endurecimiento

- Keystore, biometría y protección de capturas configurable.
- Certificate pinning con estrategia de rotación.
- SBOM, firma de artefactos y verificación de dependencias.
- Pruebas instrumentadas en Android 8 a Android 16.
- Revisión OWASP MASVS y prueba de penetración.

## Definition of Done de beta privada

La beta se considera funcional cuando tres o más teléfonos, en redes distintas, pueden registrarse con invitaciones separadas, intercambiar mensajes y notas de voz, completar llamadas de voz, recuperar mensajes tras estar offline y revocar un dispositivo sin que este vuelva a sincronizar.