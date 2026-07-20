from __future__ import annotations

import math
import tempfile
import time
from pathlib import Path

from pypdf import PdfReader

from reporting import generate_pdf_report


def _history() -> dict[str, list[tuple[float, float]]]:
    start = time.time()
    rpm = []
    maf = []
    coolant = []
    trims = []
    for index in range(180):
        timestamp = start + index * 0.1
        rpm.append((timestamp, 850 + 900 * max(0.0, math.sin(index / 22))))
        maf.append((timestamp, 3.5 + 7.2 * max(0.0, math.sin(index / 26))))
        coolant.append((timestamp, 82 + 8 * index / 180))
        trims.append((timestamp, 4.0 + 2.2 * math.sin(index / 18)))
    return {
        "RPM del motor [rpm]": rpm,
        "Flujo de aire MAF [g/s]": maf,
        "Temperatura refrigerante [°C]": coolant,
        "Corrección corta combustible B1 [%]": trims,
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "Informe_Maestro_Autoguard.pdf"
        generate_pdf_report(
            output,
            vehicle={
                "cliente": "Cliente de prueba",
                "patente": "TEST-01",
                "marca": "Chevrolet",
                "modelo": "Trax",
                "anio": "2016",
                "vin": "KL1TESTAUTOGUARD01",
                "kilometraje": "125.000 km",
                "motor": "1.8 Ecotec",
                "tecnico": "Esteban Cortez Richards",
            },
            protocol="ISO 15765-4 CAN 11/500",
            dtcs=[
                {
                    "code": "P0101",
                    "status": "Confirmado",
                    "severity": "Media-Alta",
                    "system": "Admisión / mezcla",
                    "description": "Rendimiento o rango del circuito del sensor de flujo de masa de aire MAF",
                    "symptoms": "Ralentí irregular, pérdida de potencia y consumo elevado.",
                    "causes": "MAF contaminado; ducto fisurado; fuga de vacío o PCV; filtro restringido; cableado incorrecto.",
                    "steps": "1. Guardar freeze frame.\n2. Revisar filtro y ductos.\n3. Buscar fugas de vacío y PCV.\n4. Inspeccionar y limpiar el MAF.\n5. Comparar MAF, MAP, RPM, STFT y LTFT.\n6. Reparar la causa confirmada.\n7. Borrar y validar.",
                    "validation": "Fuel trims estables, lectura MAF coherente y ausencia de P0101 después de prueba controlada.",
                    "sensors": "MAF, MAP, RPM, carga, STFT y LTFT.",
                    "tools": "Scanner, máquina de humo, multímetro y documentación OEM.",
                    "manufacturer": "SAE/ISO",
                },
                {
                    "code": "P2A00",
                    "status": "Pendiente",
                    "severity": "Media-Alta",
                    "system": "Emisiones",
                    "description": "Rendimiento del sensor de oxígeno Banco 1 Sensor 1",
                    "symptoms": "Check Engine, consumo elevado y respuesta irregular.",
                    "causes": "Sensor envejecido; fuga de escape; cableado recalentado; mezcla rica o pobre.",
                    "steps": "1. Resolver primero fallas de admisión y mezcla.\n2. Identificar B1S1.\n3. Revisar arnés y calor.\n4. Buscar fuga de escape.\n5. Evaluar respuesta rica/pobre.\n6. Reparar circuito o reemplazar solo si se confirma.\n7. Validar catalítico y reescanear.",
                    "validation": "Respuesta B1S1 dentro de criterio OEM y ausencia de P2A00 tras prueba de ruta.",
                    "sensors": "O2/A/F B1S1, STFT, LTFT, MAF y MAP.",
                    "tools": "Scanner con gráficos, multímetro, detector de fugas y documentación OEM.",
                    "manufacturer": "SAE/ISO",
                },
            ],
            live_values={
                "RPM del motor": "850 rpm",
                "Flujo de aire MAF": "4.20 g/s",
                "Temperatura refrigerante": "89 °C",
                "STFT B1": "+4.8 %",
            },
            history=_history(),
            notes="Se recomienda comprobar admisión y mezcla antes de autorizar el reemplazo del sensor de oxígeno.",
            author="Esteban Cortez Richards",
            version="6.2.2 NIVEL DIOS PREMIUM",
        )

        if not output.is_file() or output.stat().st_size < 20_000:
            raise RuntimeError("El PDF maestro no fue generado o quedó incompleto")

        reader = PdfReader(str(output))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        normalized = text.upper()

        required = (
            "INFORME TÉCNICO DE DIAGNÓSTICO Y REPARACIÓN",
            "CÓDIGOS REGISTRADOS",
            "GRÁFICOS TÉCNICOS",
            "DIAGNÓSTICO Y REPARACIÓN DEL CÓDIGO P0101",
            "DIAGNÓSTICO Y REPARACIÓN DEL CÓDIGO P2A00",
            "PLAN DE TRABAJO RECOMENDADO",
            "CHECKLIST DE ENTREGA",
            "CONCLUSIÓN TÉCNICA",
            "RECOMENDACIÓN FINAL",
        )
        for marker in required:
            if marker not in normalized:
                raise RuntimeError(f"Falta sección del informe maestro: {marker}")

        forbidden = (
            "6.2.2 NIVEL DIOS PREMIUM",
            "VERSIÓN INSTALADA",
        )
        for marker in forbidden:
            if marker in normalized:
                raise RuntimeError(f"El informe imprimió información interna no autorizada: {marker}")

        if len(reader.pages) < 6:
            raise RuntimeError(f"El informe maestro quedó demasiado corto: {len(reader.pages)} páginas")

        print(f"Informe maestro validado: {len(reader.pages)} páginas, {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
