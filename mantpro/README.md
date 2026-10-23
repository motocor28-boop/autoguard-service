# EECR / MantPro IA — sincronización automática sin correo

La aplicación funciona sin conexión y conserva los registros en el navegador (`mantpro-records-v3`). Una vez compartida una **clave privada entre el PC y el teléfono**, sincroniza automáticamente con el canal privado `eecr-device-sync` en Supabase, con independencia de si la conexión de Windows proviene del hotspot del Android o de otro router.

## Primera vinculación (única)

1. Guardar respaldos JSON en el teléfono y el computador antes de comenzar.
2. Activar compartir Internet del teléfono y conectar Windows a su Wi-Fi.
3. Abrir `https://motocor28-boop.github.io/autoguard-service/mantpro/` en el computador (Microsoft Edge).
4. Pulsar el indicador superior de sincronización; utilizar **Copiar enlace para el otro dispositivo**.
5. Abrir ese enlace en Chrome del teléfono o pegarlo en la opción de vinculación del móvil. Se crea una asociación privada, **sin correo, contraseña ni OTP**.
6. Conservar el mismo navegador y almacenamiento en ambos equipos. Los siguientes encuentros entre ambos dispositivos se sincronizan solos mientras tengan Internet.

## Protección de datos

La primera vinculación **no puede ser invisible**: debe transmitirse una clave privada de 256 bits. Sin ello, cualquier teléfono podría reclamar las OT del computador. El enlace es confidencial porque da acceso a los registros; compartirlo solamente con el propio teléfono y no publicarlo.

El servicio de Supabase utiliza una función Edge con clave administrativa **exclusivamente en el servidor**. La tabla `eecr_device_records` tiene RLS activo y prohíbe el acceso directo a usuarios anónimos o autenticados. La API obtiene un hash de la clave para aislar los historiales por canal. No se ha abierto públicamente `mantpro_records` ni se han eliminado los datos antiguos.

Si no hay cobertura de datos móviles ni salida a Internet, los registros permanecen locales y se reintentan automáticamente. La comunicación teléfono–PC ya no requiere los puertos 5000 ni 8787; el puente 8787 corresponde únicamente a la integración con la aplicación de escritorio Informe KPI.

## Limitaciones y validación

- El módulo Electron de **Informe KPI EHS** no está en este repositorio. El navegador de Windows transmite al puente local `http://127.0.0.1:8787/api/data` cuando está disponible.
- Cada registro se une por su identificador y fecha de actualización, sin borrar el historial. En una edición concurrente se guarda la versión local desplazada en `eecr-device-conflicts-v1` antes de aplicar la más nueva.
- Los registros individuales mayores de 1,85 millones de caracteres se conservan localmente, pero no se transfieren por este canal; el indicador mostrará pendiente.
- El histórico guardado en la antigua cuenta Supabase sigue intacto; no se migra automáticamente sin permiso de acceso de esa cuenta.
- **No borrar caché/almacenamiento del navegador, no desinstalar la PWA sin copia de respaldo**. Si se pierde la clave de emparejamiento local, se requiere un nuevo enlace del equipo ya emparejado.

Autor de mantenimiento documental: ESTEBAN CORTEZ.
