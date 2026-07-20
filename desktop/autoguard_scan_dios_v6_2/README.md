# AUTOGUARD SCAN DIOS v6.2 — nueva base limpia

Aplicación Windows de diagnóstico OBD-II multimarca, offline y sin licencias, bloqueos ni vencimientos.

**Autor:** Esteban Cortez Richards

## Características

- Conexión ELM327 mediante WiFi, puertos COM y simulador.
- Inicialización automática y detección de protocolo OBD-II.
- DTC confirmados, pendientes y permanentes.
- Base SQLite offline ampliada con más de 10.000 códigos únicos y definiciones genéricas/específicas.
- Datos en vivo seleccionables.
- Flujómetro directo mediante PID `015E` y estimación claramente identificada desde MAF.
- Panel con cuatro relojes analógicos profesionales y recepción RX.
- Osciloscopio de telemetría ECU en vivo.
- Pruebas funcionales guiadas y consola técnica.
- Informe PDF Premium.
- Página independiente de información y planificación.
- Inicio directo del panel principal, sin splash.
- Instalador clásico Windows e Inno Setup con desinstalador.

## Compilación local

```powershell
python -m pip install -r requirements.txt
python build_dtc_db.py
python make_icon.py
python -m pytest -q
pyinstaller --clean --noconfirm autoguard_scan.spec
```

Para compilar el Setup, abra `installer.iss` con Inno Setup 6 después de generar `dist/AUTOGUARD_SCAN_DIOS_v6.2`.

## Alcance responsable

ELM327 permite diagnóstico OBD-II genérico. Las funciones OEM, bidireccionales y las formas de onda eléctricas directas dependen del vehículo, hardware y protocolos compatibles. No sustituya componentes sin pruebas confirmatorias.
