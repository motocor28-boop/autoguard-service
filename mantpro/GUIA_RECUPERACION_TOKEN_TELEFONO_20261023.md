# EECR/MantPro — recuperación de vínculo desde Android

Reparación: 23-10-2026. No modifica `mantpro-records-v3` ni los registros de Informe KPI.

## Prueba recomendada

1. Conservar los datos instalados, sin borrar almacenamiento ni reinstalar.
2. En el teléfono, abrir EECR con Internet móvil o por Wi-Fi.
3. Entrar en la vinculación; pulsar **Enviar enlace o código** una sola vez.
4. Revisar **solo el último correo recibido**:
   - **Si contiene un enlace:** tocar el enlace desde el mismo teléfono. El enlace debe devolver a `/autoguard-service/mantpro/` y establecer una sesión.
   - **Si contiene un código numérico:** copiar los **seis dígitos** más recientes y pulsar Verificar código, sin haber abierto antes el enlace del mismo correo.
5. Si aparece `otp_expired`, no repetir el mismo código. Solicitar uno nuevo desde la aplicación y utilizar el mensaje más reciente.
6. Cuando el indicador muestre **Sincronizado**, comprobar las mismas OT en el PC, conectado al hotspot del teléfono.

## Dependencia de configuración en Supabase

Proyecto de autenticación: `gecrjlkfrcrlsjhanfjz`.

El propietario del proyecto debe comprobar en Supabase Dashboard:
- Authentication → URL Configuration → Redirect URLs: autorizar **https://motocor28-boop.github.io/autoguard-service/mantpro/**. Evitar redirigir a la página raíz.
- Authentication → Email Templates → Magic Link: el formato predeterminado envía un **enlace**, no un código de seis dígitos.
- Para usar **OTP exclusivamente numérico**, la plantilla Magic Link debe incluir la variable `{{ .Token }}` en el mensaje en vez de enviar un enlace de confirmación automático.
- No cambiar duración de los códigos para saltarse la verificación ni habilitar acceso anónimo a la tabla.

Nota: la plantilla de correo y las Redirect URLs no pueden ser verificadas ni editadas desde el código del repositorio. Requieren acceso a la configuración de Auth del proyecto.

## Comprobaciones de seguridad

- La tabla `mantpro_records` continúa protegida mediante RLS y exige una sesión de usuario.
- El teléfono y Windows usan la misma identidad para consultar los registros de ese usuario.
- Ningún parche reinicializa el historial ni elimina datos del navegador; mantener copias JSON de respaldo.
