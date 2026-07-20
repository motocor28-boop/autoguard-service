# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

numpy_datas, numpy_binaries, numpy_hidden = collect_all('numpy')
matplotlib_datas, matplotlib_binaries, matplotlib_hidden = collect_all('matplotlib')
reportlab_datas, reportlab_binaries, reportlab_hidden = collect_all('reportlab')

hidden = sorted(set(
    numpy_hidden
    + matplotlib_hidden
    + reportlab_hidden
    + collect_submodules('matplotlib.backends')
    + [
        'serial',
        'serial.tools.list_ports_windows',
        'tkinter',
        'tkinter.ttk',
        'sqlite3',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_agg',
        'superscan.professional_ui',
        'superscan.professional_reporting',
        'superscan.solution_engine',
    ]
))

analysis = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=numpy_binaries + matplotlib_binaries + reportlab_binaries,
    datas=numpy_datas + matplotlib_datas + reportlab_datas,
    hiddenimports=hidden,
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
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='SuperScan 2.0',
)
