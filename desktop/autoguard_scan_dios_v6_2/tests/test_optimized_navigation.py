from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_optimized_navigation_starts_in_menu_and_hides_build() -> None:
    source = (ROOT / "optimized_navigation_app.py").read_text(encoding="utf-8")
    assert 'self._show_page("Inicio")' in source
    assert "self.withdraw()" in source
    assert 'name = "Inicio"' in source
    assert "self.deiconify()" in source


def test_optimized_navigation_limits_hidden_rendering() -> None:
    source = (ROOT / "optimized_navigation_app.py").read_text(encoding="utf-8")
    for marker in (
        "_coalesce_live_packets",
        "_render_policy",
        'active != "Osciloscopio ECU"',
        'active == "Datos en vivo"',
        "_last_scope_redraw",
        "_last_gauge_redraw",
        "run_navigation_self_test",
    ):
        assert marker in source


def test_after_loop_is_single_cancelable_and_close_safe() -> None:
    source = (ROOT / "optimized_navigation_app.py").read_text(encoding="utf-8")
    for marker in (
        "_drain_after_id",
        "_drain_running",
        "_schedule_drain",
        "_cancel_drain_loop",
        "report_callback_exception",
        '"invalid command name"',
        "super().after_cancel",
    ):
        assert marker in source


def test_launcher_exposes_silent_self_test_without_fatal_dialog() -> None:
    source = (ROOT / "final_launcher.py").read_text(encoding="utf-8")
    assert '"--autoguard-self-test" in sys.argv' in source
    assert "run_navigation_self_test()" in source
    assert "OptimizedNavigationApp" in source
    assert "SystemExit(23)" in source
    assert "raise SystemExit(1)" in source


def test_patch_installer_has_full_backup_healthcheck_and_rollback() -> None:
    source = (ROOT / "patch_installer.iss").read_text(encoding="utf-8")
    for marker in (
        "CreateInstallationBackup",
        "RunApplicationSelfTest",
        "RestorePreviousInstallation",
        "FailAndRollback",
        "DeinitializeSetup",
        "GetCustomSetupExitCode",
        "--autoguard-self-test",
        "Instalacion_anterior",
        "RollbackExitCode",
        "GetDateTimeString('yyyymmdd_hhnnss', #0, #0)",
    ):
        assert marker in source
    assert "BeforeInstall: PreparePatch" not in source


def test_report_master_requirements_remain_active() -> None:
    source = (ROOT / "reporting.py").read_text(encoding="utf-8")
    for marker in (
        "INFORME TÉCNICO DE DIAGNÓSTICO Y",
        "GRÁFICO VECTORIAL HD",
        "PLAN DE TRABAJO RECOMENDADO",
        "CHECKLIST DE ENTREGA",
        "RECOMENDACIÓN FINAL",
        "_review_suggestions",
    ):
        assert marker in source
    assert '["VERSIÓN"' not in source
