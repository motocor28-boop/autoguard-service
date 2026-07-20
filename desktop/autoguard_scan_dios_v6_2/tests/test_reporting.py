from __future__ import annotations

from pathlib import Path

from reporting import generate_pdf_report


def test_report_without_visible_version_and_with_subreport(tmp_path: Path) -> None:
    source = (Path(__file__).resolve().parents[1] / "reporting.py").read_text(encoding="utf-8")
    assert '"Versión", version' not in source
    assert 'f"AUTOGUARD SCAN DIOS v{version}' not in source
    assert "SUBINFORME TÉCNICO DE PROCEDIMIENTOS" in source
    assert "PROCEDIMIENTO PASO A PASO" in source
    assert "Registro técnico" in source

    output = tmp_path / "informe_prueba.pdf"
    generate_pdf_report(
        output=output,
        vehicle={
            "cliente": "Cliente prueba",
            "patente": "TEST-01",
            "marca": "Marca",
            "modelo": "Modelo",
            "anio": "2026",
            "vin": "VINPRUEBA123456789",
            "kilometraje": "1000",
            "motor": "Motor prueba",
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
                "steps": "1. Guardar freeze frame.\n2. Revisar bujía y bobina.\n3. Verificar inyector.\n4. Medir compresión.",
                "sensors": "RPM, carga, trims y contador de fallas.",
                "tools": "Escáner, multímetro, osciloscopio y compresímetro.",
                "validation": "Borrar DTC después de reparar, realizar ciclo de prueba y confirmar que no reaparezca.",
            }
        ],
        live_values={"RPM del motor": "850 rpm", "Voltaje módulo": "14.1 V"},
        history={},
        notes="Prueba de generación de informe.",
        author="Esteban Cortez Richards",
        version="6.2.2 NIVEL DIOS PREMIUM",
    )
    assert output.is_file()
    assert output.stat().st_size > 5_000
