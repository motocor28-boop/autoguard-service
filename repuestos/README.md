# REPUESTOS IA · LEVANTAMIENTO CLOUD v3.0.0

PWA para levantamiento técnico e inventario de repuestos sin uso para clientes desde teléfono o computador.

Dirección oficial: `https://motocor28-boop.github.io/autoguard-service/repuestos/`

## Ficha de terreno

Cada registro conserva cliente, contrato, faena, campaña, folio, código, P/N, serie, fabricante, cantidad, ubicación, equipo/familia/TAG/sistema, génesis del repuesto, estado físico, clasificación de uso, reparabilidad, criticidad, almacenamiento, embalaje, documentación, obsolescencia, valor estimado, disposición, recomendación y hasta tres fotografías.

## Clasificación

Uso: Apto para uso / Uso condicionado / No apto / Pendiente.

Reparabilidad: No requiere reparación / Reparable / No reparable / Pendiente.

Génesis: sobrecompra, proyecto terminado, cambio de alcance, equipo dado de baja, contingencia, devolución de mantenimiento, recuperación/desarme, obsolescencia, compra errónea, no determinada u otra.

## Terreno y respaldo

La PWA trabaja offline-first. Sin señal, la ficha y sus fotos quedan respaldadas localmente; al recuperar Internet se sincronizan con Supabase Cloud.

**Respaldar jornada** genera un ZIP con Excel diario, JSON de recuperación y fotografías del día. En teléfonos compatibles puede compartirse con el menú nativo de Android.

## Excel

El reporte incluye RESUMEN AVANCE, LEVANTAMIENTO HOY/MAESTRO ACUMULADO, POR EQUIPO, POR GENESIS, POR USO, POR REPARABILIDAD, POR DISPOSICION y PENDIENTES.
