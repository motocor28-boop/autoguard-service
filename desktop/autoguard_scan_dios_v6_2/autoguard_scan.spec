# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("reportlab")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("data/autoguard_dtc.sqlite", "data"),
        ("THIRD_PARTY_NOTICES.txt", "."),
        ("autoguard.ico", "."),
        ("autoguard.png", "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AUTOGUARD_SCAN_DIOS_v6.2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="autoguard.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AUTOGUARD_SCAN_DIOS_v6.2",
)
