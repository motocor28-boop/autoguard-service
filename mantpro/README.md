# MANTPRO IA Cloud

PWA movil para registrar mantencion y seguridad desde cualquier dispositivo. La aplicacion guarda los registros localmente hasta que se configura la sincronizacion con Supabase.

## Activacion de nube

Cree un proyecto Supabase, ejecute el esquema SQL, agregue la URL y anon key al archivo config.js y proteja los registros con RLS y magic link. Nunca exponga una key service_role.