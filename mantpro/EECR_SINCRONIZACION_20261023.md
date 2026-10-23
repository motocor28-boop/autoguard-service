# EECR / MantPro — sincronización teléfono, PC e Informe KPI

**Revisión:** 2026-10-23
**Entorno:** web móvil/Windows (`mantpro/`) + Informe KPI local que ofrece `/api/data` en `http://127.0.0.1:8787`.

## Flujo habilitado

1. El teléfono guarda nuevas OT, avances, desviaciones, caminatas, charlas, fotos y evaluaciones en `mantpro-records-v3` mientras no haya señal.
2. Cuando recupera datos móviles o comparte Internet mediante hotspot, el teléfono y el PC se conectan a Supabase con **la misma identidad autenticada**.
3. El sistema lee el historial remoto antes de escribir; solo inserta registros ausentes o actualizaciones locales pendientes. Los identificadores heredados se convierten de forma determinística a UUID, sin cambiar el ID interno.
4. El navegador del PC recupera los registros remotos y los envía al puente **local** en el puerto 8787, si el programa Informe KPI está abierto y ofrece el API anterior.
5. Los registros existentes en el escritorio se conservan; el traspaso añade o actualiza por ID y fecha, **sin borrar arrays ajenos ni resetear bases de datos**.

## Procedimiento de uso

- **Antes de cualquier actualización:** exportar respaldo JSON en teléfono y PC desde el menú `Más`. Guardar aparte los archivos resultantes.
- Activar zona Wi-Fi del Android y conectar Windows a esa red.
- Abrir la web EECR en ambos dispositivos. Tocar la etiqueta superior de sincronización para verificar la **misma cuenta** por correo, una sola vez por dispositivo.
- Confirmar que ambos muestran `Sincronizado`; los datos locales permanecen incluso cuando el servidor temporalmente no responde.
- Abrir Informe KPI en Windows; si su servidor local está operativo en `127.0.0.1:8787`, el navegador del PC intenta actualizarlo después de cada sincronización y cada 20 segundos mientras está visible.
- Reabrir o recargar los informes y KPI después de una importación. Confirmar totales de OT, avances, seguridad y disponibilidad con el historial original.

## Diagnóstico de red

En PowerShell de Windows (no modifica datos):
```powershell
Get-NetTCPConnection -State Listen -LocalPort 8787 -ErrorAction SilentlyContinue
Invoke-WebRequest -Uri 'http://127.0.0.1:8787/api/data' -UseBasicParsing -TimeoutSec 5
```

Si el primer comando no devuelve ningún resultado o el segundo no responde, el servidor de **Informe KPI** no está iniciado. No instalar el reparador del puerto 5000: pertenece a la versión ajena de MantPro/AnabasaSoft.

## Límites de esta reparación

- La ruta Cloud funciona si hay Internet por el teléfono u otra red. Conectar los equipos solo por Wi-Fi sin Internet no equivale a una sincronización local independiente; esa función exigiría servidor LAN y adaptar la PWA al origen/HTTPS.
- El módulo Windows de Informe KPI no es parte de este repositorio. No se modificó su ejecutable ni sus estructuras internas. El puente nuevo sigue su API `/api/data` existente, cuyo funcionamiento debe comprobarse en el computador real.
- Los cambios simultáneos del mismo registro que sean más recientes en la nube no se sobrescriben automáticamente con una versión local más antigua. La divergencia local permanece pendiente de conciliación.
- Para mantener seguridad, la nube exige una sesión autenticada; el modo de trabajo local sigue abierto si no hay sesión.
- No borrar datos del navegador, desinstalar la PWA ni seleccionar reinicio total antes de verificar copias de respaldo.

## Evidencia técnica revisada

- Supabase (proyecto existente): reactivado y `ACTIVE_HEALTHY` al 23-10-2026. Tabla `mantpro_records` existente con RLS por identidad.
- Archivos modificados: `auth.js`, `app.js`, `index.html`, `sw.js`, `instalar.html`.
- Archivo agregado: `eecr-kpi-live-bridge.js`.
- Verificación de sintaxis de JavaScript: aprobada.
- Prueba simulada del puente: conserva una OT preexistente, incorpora una OT nueva, un avance y una desviación, sin eliminar arrays.
- **Pendiente:** prueba de conectividad y cálculo real KPI en el equipo Windows del usuario y verificación OTP por correo en ambos dispositivos.
