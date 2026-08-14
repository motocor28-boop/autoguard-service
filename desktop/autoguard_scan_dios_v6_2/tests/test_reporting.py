from __future__ import annotations

import math
import time
from pathlib import Path

from reporting import generate_pdf_report


def test_report_master_without_visible_version_and_with_procedures(tmp_path: Path) -> None:
    source = (Path(__file__).resolve().parents[1] / "reporting.py").read_text(encoding="utf-8")
    assert '"Versión", version' not in source
    assert 'f"AUTOGUARD SCAN DIOS v{version}' not in source
    assert "INFORME TÉCNICO DE DIAGNÓSTICO Y" in source
    assert "GRÁFICO VECTORIAL HD" in source
    assert "DIAGNÓSTICO Y REPARACIÓN DEL CÓDIGO" in source
    assert "PLAN DE TRABAJO RECOMENDADO" in source
    assert "CHECKLIST DE ENTREGA" in source
    assert "RECOMENDACIÓN FINAL" in source
    assert "_review_suggestions" in source

    start = time.time()
    history = {
        "RPM del motor [rpm]": [
            (start + index * 0.1, 850 + 350 * max(0.0, math.sin(index / 10)))
            for index in range(100)
        ],
        "Flujo de aire MAF [g/s]": [
            (start + index * 0.1, 3.8 + 2.4 * max(0.0, math.sin(index / 13)))
            for index in range(100)
        ],
    }

    output = tmp_path / "informe_maestro_prueba.pdf"
    generate_pdf_report(
        output=output,
        vehicle={
            "cliente": "Cliente prueba",
            "patente": "TEST-01",
            "marca": "Chevrolet",
            "modelo": "Trax",
            "anio": "2016",
            "vin": "VINPRUEBA123456789",
            "kilometraje": "1000",
            "motor": "1.8 Ecotec",
            "tecnico": "Esteban Cortez Richards",
        },
        protocol="ISO 15765-4 CAN",
        dtcs=[
            {
                "code": "P0301",
                "status": "Confirmado",
                "severity": "Alta",
                "system": "Encendido / combustión",
                "description": "Falla de encendido cilindro 1",
                "manufacturer": "Genérico",
                "symptoms": "Ralentí irregular y pérdida de potencia.",
                "causes": "Bujía, bobina, inyector, compresión o cableado.",
                "steps": "1. Guardar freeze frame.\n2. Revisar bujía y bobina.\n3. Verificar inyector.\n4. Medir compresión.\n5. Reparar la causa confirmada.\n6. Borrar y validar.",
                "sensors": "RPM, carga, trims y contador de fallas.",
                "tools": "Escáner, multímetro, osciloscopio y compresímetro.",
                "validation": "Borrar DTC después de reparar, realizar ciclo de prueba y confirmar que no reaparezca.",
            }
        ],
        live_values={"RPM del motor": "850 rpm", "Voltaje módulo": "14.1 V"},
        history=history,
        notes="Prueba de generación del informe técnico maestro.",
        author="Esteban Cortez Richards",
        version="6.2.2 NIVEL DIOS PREMIUM",
    )
    assert output.is_file()
    assert output.stat().st_size > 10_000
