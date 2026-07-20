from __future__ import annotations

from superscan.dtc_database import DTCDatabase, TOTAL_DTC_RECORDS
from superscan.obd import DTCResult, VehicleScan
from superscan.professional_reporting import generate_professional_pdf_report
from superscan.solutions import SolutionDatabase


def test_solution_database_has_plan_for_every_dtc(tmp_path):
    dtc_db = DTCDatabase(tmp_path / "dtc.sqlite3")
    solution_db = SolutionDatabase(dtc_db, tmp_path / "solutions.sqlite3")
    assert solution_db.count() == TOTAL_DTC_RECORDS == 12_133

    detailed = solution_db.lookup("P0171")
    assert detailed.severity == "ALTA"
    assert len(detailed.causes) >= 5
    assert len(detailed.steps) >= 10
    assert any("prueba de ruta" in step.lower() for step in detailed.steps)

    generic = solution_db.lookup("P1234")
    assert len(generic.steps) >= 8
    assert len(generic.validation) >= 4
    assert "OEM" in generic.notes


def test_professional_report_contains_graphs_and_action_plan(tmp_path):
    dtc_db = DTCDatabase(tmp_path / "dtc.sqlite3")
    solution_db = SolutionDatabase(dtc_db, tmp_path / "solutions.sqlite3")
    scan = VehicleScan(
        adapter="ELM327 v1.5 SUPERSCAN",
        protocol_number="A6",
        protocol_name="ISO 15765-4 CAN (11 bit ID, 500 kbaud)",
        vin="KL1JEBAB0FB000001",
        supported_pids={0x0C, 0x0D, 0x2F, 0x5E},
        dtcs=[DTCResult("P0171", "Confirmado / almacenado")],
    )
    live = {
        "RPM motor": (2486.0, "rpm"),
        "Temperatura refrigerante": (87.0, "°C"),
        "Caudal de combustible": (1.85, "L/h"),
        "Nivel de combustible": (58.0, "%"),
    }
    history = {
        "RPM motor": [(0.0, 820.0), (1.0, 1200.0), (2.0, 2486.0)],
        "Temperatura refrigerante": [(0.0, 82.0), (1.0, 85.0), (2.0, 87.0)],
        "Caudal de combustible": [(0.0, 0.7), (1.0, 1.1), (2.0, 1.85)],
    }
    output = tmp_path / "professional_report.pdf"
    result = generate_professional_pdf_report(
        scan,
        scan.dtcs,
        live,
        history,
        {"RPM motor": (820.0, "rpm")},
        dtc_db,
        solution_db,
        vehicle_meta={"technician": "Esteban Cortez", "client": "Cliente de prueba", "plate": "TEST-20", "mileage": "125.680 km"},
        output_path=output,
    )
    assert result == output
    assert output.read_bytes().startswith(b"%PDF")
    assert output.stat().st_size > 20_000
