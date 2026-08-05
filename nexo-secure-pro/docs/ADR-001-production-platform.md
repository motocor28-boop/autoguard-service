# ADR-001: plataforma de producción de Nexo Secure Pro

Estado: aceptada
Fecha: 2026-08-05

## Objetivo

Construir una aplicación Android nativa para varios teléfonos, con registro cerrado, mensajería cifrada de extremo a extremo, notas de voz, archivos, llamadas de voz 1:1, revocación de dispositivos y administración privada.

## Decisión

La plataforma no continuará sobre la WebView ni sobre el cifrado experimental del prototipo.

### Cliente Android

- Kotlin y Jetpack Compose.
- Matrix Rust SDK mediante bindings oficiales para sincronización, almacenamiento y cifrado de extremo a extremo.
- Android Keystore para proteger secretos del dispositivo.
- Base local cifrada, bloqueo biométrico y ocultación del contenido en notificaciones.
- LiveKit Android SDK para audio en tiempo real.

### Servidor de mensajería

- Tuwunel 1.6.x, Matrix homeserver estable escrito en Rust y licenciado Apache-2.0.
- Federación desactivada en la primera versión: red privada y cerrada.
- Registro habilitado únicamente mediante invitaciones de uso limitado.
- Los números telefónicos serán identificadores de acceso administrativos y no nombres públicos.

### Llamadas

- LiveKit Server autohospedado.
- Servicio propio de emisión de JWT para no depender de componentes AGPL ajenos.
- Salas 1:1, permisos mínimos, expiración corta y creación controlada por el backend.
- Cifrado de medios del cliente y TLS obligatorio.

### Servicios de plataforma

- Caddy como terminación TLS y proxy inverso.
- PostgreSQL para administración, invitaciones, auditoría y dispositivos autorizados.
- Redis para presencia, sesiones breves, límites y coordinación de llamadas.
- Docker Compose para beta privada y Kubernetes solamente cuando la carga lo justifique.

## Identidad y registro

1. El administrador carga o invita un número autorizado.
2. La aplicación valida una invitación de un solo uso.
3. El teléfono crea su identidad criptográfica y registra el dispositivo.
4. Un dispositivo nuevo requiere aprobación o verificación desde un dispositivo existente.
5. El número queda oculto para otros usuarios, salvo que el administrador permita mostrarlo.

## Alcance de la beta funcional

- Instalación en varios teléfonos Android.
- Registro cerrado y revocación.
- Mensajes 1:1 cifrados.
- Confirmaciones, escritura, cola offline y mensajes temporales.
- Notas de voz y archivos cifrados.
- Llamadas de voz 1:1 reales.
- Panel administrativo web.
- Copias de seguridad cifradas del servidor.

## Criterios para llamarla comercial

La aplicación no se anunciará como comercial ni apta para información sensible hasta completar:

- pruebas en dispositivos reales y redes móviles distintas;
- revisión de dependencias y licencias;
- OWASP MASVS/MASTG;
- análisis estático, dinámico y de cadena de suministro;
- prueba de penetración;
- auditoría criptográfica externa;
- firma de producción y canal de actualizaciones;
- política de privacidad, términos y respuesta a incidentes.

## Declaración de seguridad

No existe software 100 % invulnerable. El objetivo es seguridad verificable, reducción de superficie de ataque, cifrado extremo a extremo y capacidad de corregir y distribuir actualizaciones rápidamente.