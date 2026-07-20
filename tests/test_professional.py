from __future__ import annotations

from superscan.dtc_database import DTCDatabase, TOTAL_DTC_RECORDS
from superscan.obd import DTCResult, VehicleScan
from superscan.professional_reporting import generate_professional_report
from superscan.solution_engine import OfflineSolutionDatabase


def test_offline_solution_catalog(tmp_path):
    db_path = tmp_path / "professional.sqlite3"
    dtc = DTCDatabase(db_path)
    solutions = OfflineSolutionDatabase(db_path)
    assert dtc.count() == solutions.count() == TOTAL_DTC_RECORDS == 12_133
    guide = solutions.lookup("P0171")
    assert guide.severity == "ALTA"
    assert len(guide.steps) >= 8
    assert "vacío" in " ".join(guide.causes).lower()
    generic = solutions.lookup("C1234", dtc.lookup("C1234").description, "Chasis")
    assert generic.steps
    assert generic.validation


def test_professional_report_with_graphs(tmp_path):
    db_path = tmp_path / "professional.sqlite3"
    dtc = DTCDatabase(db_path)
    solutions = OfflineSolutionDatabase(db_path)
    scan = VehicleScan(
        adapter="ELM327 v1.5 SUPERSCAN",
        protocol_number="A6",
        protocol_name="ISO 15765-4 CAN (11 bit ID, 500 kbaud)",
        vin="KL1JEBAB0FB000001",
        supported_pids={0x0C, 0x0D, 0x05, 0x2F, 0x5E},
        monitor_raw="41 01 83 07 65 00",
        dtcs=[DTCResult("P0171", "Confirmado / almacenado"), DTCResult("P0420", "Pendiente")],
    )
    live = {
        "RPM motor": (2486.0, "rpm"),
        "Temperatura refrigerante": (87.0, "°C"),
        "Ajuste combustible corto B1": (-2.3, "%"),
        "Ajuste combustible largo B1": (1.6, "%"),
        "Caudal de combustible": (1.85, "L/h"),
        "Nivel de combustible": (58.0, "%"),
    }
    history = {
        name: [(float(index), float(value) + index * 0.02) for index in range(20)]
        for name, (value, _unit) in live.items()
    }
    output = tmp_path / "informe_profesional.pdf"
    result = generate_professional_report(
        scan,
        scan.dtcs,
        live,
        history,
        dtc,
        solutions,
        {"tecnico": "Esteban Cortez", "cliente": "Prueba", "vehiculo": "Vehículo demo"},
        output,
    )
    assert result == output
    assert output.exists()
    assert output.stat().st_size > 20_000
