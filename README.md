# SuperScan 2.0 Final Mejorado

Aplicación de diagnóstico automotriz multimarca para Windows desarrollada para AutoGuard Servicios.

## Funciones integradas

- Conexión ELM327 por puerto COM y Wi-Fi TCP.
- Simulador integrado con protocolo ISO 15765-4 CAN.
- Detección automática del protocolo OBD-II.
- Identificación VIN y disponibilidad de PIDs.
- Lectura de DTC confirmados, pendientes y permanentes.
- Borrado de códigos con confirmación.
- Base offline de 12.133 códigos y descripciones propias/genéricas.
- Datos en vivo, incluidos PID 015E (caudal de combustible) y PID 012F (nivel de combustible).
- Gráficos técnicos HD con historial de sesión.
- Freeze Frame y monitores OBD-II.
- Informe PDF AutoGuard.
- Registro rotativo de comunicación y errores.
- Instalación por usuario en `%LOCALAPPDATA%\SuperScan\2.0 Final Mejorado`.

## Validación

```powershell
pip install -r requirements.txt
pytest -q
pyinstaller --noconfirm --clean superscan.spec
```

El instalador se genera con Inno Setup mediante `installer.iss`.

## Separación de proyectos

Este código pertenece exclusivamente a SuperScan 2.0 y no utiliza módulos, nombres ni archivos de AutoGuard Scan DIOS v6.2.
