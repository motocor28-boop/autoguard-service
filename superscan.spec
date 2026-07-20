# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

matplotlib_datas = collect_data_files('matplotlib')
reportlab_datas = collect_data_files('reportlab')
hidden = collect_submodules('matplotlib.backends') + collect_submodules('reportlab')

analysis = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=matplotlib_datas + reportlab_datas,
    hiddenimports=hidden + [
        'serial',
        'serial.tools.list_ports_windows',
        'tkinter',
        'tkinter.ttk',
        'sqlite3',
        'matplotlib.backends.backend_tkagg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='SuperScan 2.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SuperScan 2.0',
)
