# Nexo Secure Pro v1

Rama de reconstrucción comercial de Nexo Secure.

## Objetivo

Aplicación privada Android/iOS con registro cerrado, mensajería E2EE, notas de voz, llamadas 1:1, panel administrativo y mínima metadata.

## Estado actual

Se inició la base comercial y el backend de transporte opaco. El servidor registra dispositivos previamente invitados y retransmite sobres `ciphertext` sin interpretar su contenido. Esta etapa es funcional para desarrollo, pero todavía no debe utilizarse para comunicaciones sensibles.

## Arquitectura aprobada

- Android: Kotlin + Jetpack Compose.
- iOS: Swift + SwiftUI.
- Backend: Go.
- Datos: PostgreSQL.
- Voz: WebRTC + TURN.
- Claves: Android Keystore y Apple Keychain/Secure Enclave.
- Seguridad: OWASP MASVS/MASTG.
- E2EE: implementación auditada con ratchet; queda prohibido inventar un protocolo criptográfico propio para producción.

## Puertas antes de producción

1. Modelo de amenazas y revisión de licencias.
2. E2EE auditado y almacenamiento seguro de claves.
3. Pruebas móviles, API, dependencias y penetración.
4. Auditoría criptográfica externa.
5. Infraestructura, monitoreo, respuesta a incidentes y políticas legales.

El paquete completo de fundación incluye backend Go funcional, pruebas automatizadas, Docker, consola técnica y documentación de arquitectura y seguridad.